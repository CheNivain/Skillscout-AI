"""Behavioural tests for IR, grounded generation, temporal offers and scoring."""
import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from backend.ai import engine
from backend.ai.taxonomy import extract_learning_entities, extract_skills
from backend.data.seed import get_seed_courses, get_seed_posts
from backend.evaluation import mrr, ndcg_at_k, precision_at_k, recall_at_k, run_evaluation

_REAL_COMPLETE = engine._complete_llm


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch):
    monkeypatch.setattr(engine, '_complete_llm', lambda *args: (None, None))


@pytest.fixture
def profile():
    return {'role_title': 'Data Analyst', 'career_goal': 'Data Scientist', 'skills': ['SQL', 'Excel', 'Power BI'],
            'certifications': [], 'training_history': [], 'experience_years': 3, 'weekly_hours': 6,
            'budget': 80, 'interests': [], 'bio': ''}


@pytest.fixture
def courses():
    return get_seed_courses()


def test_profile_gaps_and_unknown_skills_are_preserved(profile):
    profile['skills'].append('Django')
    needs = engine.analyze_profile(profile)
    assert {'Python', 'Statistics', 'Machine Learning'} <= set(needs['skill_gaps'])
    assert not {'SQL', 'Excel', 'Power BI'} & set(needs['skill_gaps'])
    assert 'Django' in needs['current_skills']
    assert needs['priority_skills'].index('Python') < needs['priority_skills'].index('Machine Learning')
    assert needs['priority_skills'].index('Statistics') < needs['priority_skills'].index('Machine Learning')
    assert needs['llm_used'] is False and needs['model'] is None


def test_profile_certifications_and_completed_training_reduce_gaps(profile):
    profile['certifications'] = ['Python professional certificate']
    profile['training_history'] = ['Introduction to Statistics']
    needs = engine.analyze_profile(profile)
    assert 'Python' not in needs['skill_gaps'] and 'Statistics' not in needs['skill_gaps']


def test_ir_explicit_query_overrides_different_employee_goal(profile, courses):
    results = engine.retrieve_courses(courses, engine.analyze_profile(profile), [], query='azure cloud fundamentals certification')
    assert results[0]['course']['id'] == 'azure-fundamentals'
    assert all(set(row['matched_skills']) <= {'Azure', 'Cloud Computing'} for row in results)


def test_ir_does_not_mark_every_skill_matched(courses):
    result = engine.retrieve_courses(courses, {}, [], query='Python')
    assert result and all(row['matched_skills'] == ['Python'] for row in result if 'Python' in row['course']['skills'])
    assert all('Docker' not in row['matched_skills'] for row in result)
    assert engine.retrieve_courses(courses, {}, [], query='zzzznonexistent') == []
    assert engine.retrieve_courses([], {}, [], query='Python') == []
    assert engine.retrieve_courses(courses, {}, [], query='Python', limit=0) == []


def test_ir_aliases_and_real_cosine():
    index = engine.HybridIndex(['Python', 'Python Python', 'Azure cloud'])
    assert index._cosine(['python'])[0] == pytest.approx(1)
    assert index.rank('Azure')[2] > index.rank('Azure')[0]
    assert engine.HybridIndex(['Python'])._cosine(['python']) == [1]
    assert extract_skills('k8s and scikit-learn') == ['Machine Learning', 'Kubernetes']


def test_nlp_word_boundaries_entities_and_deduplication():
    entities = extract_learning_entities('I completed Azure AI Fundamentals with Microsoft Learn. Python python.')
    assert 'Azure AI Fundamentals' in entities['certification']
    assert entities['provider'] == ['Microsoft Learn']
    assert entities['skill'].count('Python') == 1
    assert 'Git' not in extract_skills('digital agility')


def test_trends_use_two_windows_and_skip_future_invalid_old_posts():
    now = datetime.now(timezone.utc)
    def post(i, days, text='Python Python'):
        return {'id': str(i), 'text': text, 'published_at': (now - timedelta(days=days)).isoformat(), 'is_demo': True}
    posts = [post(1, 1), post(2, 3), post(3, 20), post(4, 40), post(5, -1), {'id': 'bad', 'text': 'Python', 'published_at': 'bad'}]
    trend = engine.discover_trends(posts)[0]
    assert trend['mentions'] == 3 and trend['growth_percent'] == 100
    assert trend['current_mentions'] == 2 and trend['prior_mentions'] == 1
    assert {item['id'] for item in trend['evidence']} == {'1', '2', '3'}
    assert 'corpus statistic' in trend['summary']
    assert trend['llm_used'] is False


def test_expired_offers_restore_original_price_without_mutation(courses):
    raw = next(c for c in courses if c['id'] == 'nlp-specialization')
    before = copy.deepcopy(raw)
    effective = engine.effective_course(raw)
    assert effective['price'] == raw['original_price'] and effective['discount_percent'] == 0
    assert effective['offer_expired'] is True and raw == before
    assert engine.effective_course(effective) == effective
    raw['offer_expires_at'] = 'malformed'
    assert engine.effective_course(raw)['discount_percent'] == 0


def test_only_offers_with_valid_future_expiry_remain(courses):
    course = copy.deepcopy(courses[0])
    assert engine.effective_course(course)['discount_percent'] == 70
    course['offer_expires_at'] = None
    assert engine.effective_course(course)['discount_percent'] == 0


def test_recommendations_have_reconstructable_scores_and_real_source_ids(profile, courses):
    needs = engine.analyze_profile(profile)
    posts = get_seed_posts()
    trends = engine.discover_trends(posts, needs)
    results = engine.recommend(profile, needs, trends, engine.retrieve_courses(courses, needs, trends))
    assert results and results[0]['priority'] == 'high'
    valid_sources = {c['id'] for c in courses} | {p['id'] for p in posts}
    for row in results:
        assert row['score'] == pytest.approx(round(sum(row['factors'][k] * v for k, v in engine.FACTOR_WEIGHTS.items()), 1))
        assert all(0 <= n <= 100 for n in row['factors'].values())
        assert set(row['source_ids']) <= valid_sources
        assert set(row['matched_skills']) <= set(needs['target_skills'])
    assert 'deep-learning' not in {r['id'] for r in results}


def test_completed_courses_excluded_and_irrelevant_discounts_cannot_win(profile, courses):
    needs = engine.analyze_profile(profile)
    profile['training_history'] = ['python-data-science', 'Python']  # title of the Kaggle course
    candidates = [{'course': c, 'retrieval_score': 1, 'matched_skills': c['skills']} for c in courses]
    results = engine.recommend(profile, needs, [], candidates)
    assert not {'python-data-science', 'kaggle-python', 'docker-started', 'azure-fundamentals'} & {r['id'] for r in results}


def test_free_budget_and_prerequisite_fit_affect_recommendations(profile, courses):
    needs = engine.analyze_profile(profile)
    candidates = [{'course': c, 'retrieval_score': 1} for c in courses]
    profile['budget'] = 0
    results = engine.recommend(profile, needs, [], candidates)
    assert results[0]['course']['price'] == 0
    paid = next(r for r in results if r['id'] == 'python-data-science')
    assert 'exceeds your USD 0 budget' in paid['explanation']
    assert 'Python' not in next(r for r in results if r['id'] == 'python-data-science')['missing_prerequisites']


def test_sensitive_irrelevant_profile_attributes_do_not_change_ranking(profile, courses):
    needs = engine.analyze_profile(profile)
    candidates = engine.retrieve_courses(courses, needs, [])
    first = engine.recommend(profile, needs, [], candidates)
    second = engine.recommend({**profile, 'age': 70, 'gender': 'female', 'religion': 'none'}, needs, [], candidates)
    assert [(r['id'], r['score']) for r in first] == [(r['id'], r['score']) for r in second]


def test_profile_llm_can_only_select_known_gaps_and_respects_prerequisites(profile, monkeypatch):
    monkeypatch.setattr(engine, '_complete_llm', lambda *args: ('{"priority_skills":["Machine Learning"]}', 'test-local'))
    needs = engine.analyze_profile(profile)
    assert needs['llm_used'] and needs['priority_skills'][:3] == ['Python', 'Statistics', 'Machine Learning']
    monkeypatch.setattr(engine, '_complete_llm', lambda *args: ('{"priority_skills":["Invented Skill"],"summary":"You need a paid scam"}', 'test-local'))
    needs = engine.analyze_profile(profile)
    assert not needs['llm_used'] and 'scam' not in needs['summary']


@pytest.mark.parametrize('model_response', [
    'Buy this made-up course for USD 9999 at https://evil.example',
    '{"course_ids":["invented"],"focus":"career"}',
    '{"course_ids":["kaggle-python"],"focus":"budget","price":9999}',
    '{"course_ids":[{}],"focus":"budget"}',
    '{"course_ids":["kaggle-python"],"focus":["budget"]}',
])
def test_chat_rejects_hallucinated_or_malformed_llm_output(profile, courses, monkeypatch, model_response):
    needs = engine.analyze_profile(profile)
    monkeypatch.setattr(engine, '_complete_llm', lambda *args: (model_response, 'test-local'))
    result = engine.answer_question('Python beginner courses', profile, courses, needs)
    assert result['sources'] and result['llm_used'] is False
    assert '9999' not in result['answer'] and 'evil.example' not in result['answer']
    assert result['model'] is None


def test_chat_accepts_valid_grounded_plan_and_renders_facts(profile, courses, monkeypatch):
    needs = engine.analyze_profile(profile)
    monkeypatch.setattr(engine, '_complete_llm', lambda *args: ('{"course_ids":["kaggle-python"],"focus":"budget"}', 'test-local'))
    result = engine.answer_question('Python beginner courses', profile, courses, needs)
    assert result['llm_used'] is True and result['model'] == 'test-local'
    assert [c['id'] for c in result['sources']] == ['kaggle-python']
    assert 'USD 0' in result['answer'] and 'sample prices' in result['answer']


def test_chat_returns_no_sources_for_unrelated_question(profile, courses):
    result = engine.answer_question('zzzznonexistent', profile, courses)
    assert result['sources'] == [] and not result['llm_used']
    assert engine.answer_question('What should I learn next?', profile, courses)['sources']


def test_expired_sale_not_advertised_in_chat(profile, courses):
    course = next(c for c in courses if c['id'] == 'nlp-specialization')
    result = engine.answer_question('NLP', profile, [course])
    assert result['sources'][0]['price'] == 149
    assert 'USD 149' in result['answer'] and 'Expired discount excluded' in result['answer']


def test_metrics_against_hand_calculated_ranking():
    ranked, relevant = ['wrong', 'a', 'b'], {'a', 'b'}
    assert precision_at_k(ranked, relevant, 2) == .5
    assert recall_at_k(ranked, relevant, 2) == .5
    assert mrr(ranked, relevant) == .5
    assert ndcg_at_k(['a', 'b'], relevant, 2) == 1
    assert ndcg_at_k([], relevant, 2) == 0
    with pytest.raises(ValueError):
        run_evaluation(0)
    report = run_evaluation()
    assert report['queries'] == 7 and report['macro_mrr'] >= .7


def test_seed_contract_and_provenance():
    from backend.config import CourseInput, PostInput
    courses = get_seed_courses()
    assert len(courses) >= 24 and len(get_seed_posts()) >= 35
    assert len({c['id'] for c in courses}) == len(courses)
    for course in courses:
        assert course['is_demo'] and course['url'].startswith('https://')
        CourseInput.model_validate({k: v for k, v in course.items() if k != 'id'})
    for post in get_seed_posts():
        assert post['is_demo'] and post['source_url'] is None
        PostInput.model_validate({k: v for k, v in post.items() if k != 'id'})


@pytest.mark.parametrize('installed, expected', [('qwen2.5:7b', False), ('qwen2.5:3b', True)])
def test_ollama_status_requires_exact_model_tag(monkeypatch, installed, expected):
    import httpx
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.setenv('OLLAMA_MODEL', 'qwen2.5:3b')
    monkeypatch.setattr(engine, '_STATUS_CACHE', None)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={'models': [{'name': installed}]}))
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(engine.httpx, 'Client', lambda **kwargs: client)
    result = engine.get_model_status()
    assert result['llm_available'] is expected


def test_real_llm_adapter_posts_bounded_json_request(monkeypatch):
    import httpx
    monkeypatch.setenv('OLLAMA_MODEL', 'qwen2.5:3b')
    monkeypatch.setattr(engine, 'get_model_status', lambda: {'llm_available': True, 'provider': 'ollama'})
    observed = {}
    def respond(request):
        observed.update(json.loads(request.content))
        assert request.url.path == '/api/chat'
        return httpx.Response(200, json={'message': {'content': '{"course_ids":["kaggle-python"],"focus":"general"}'}})
    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(engine.httpx, 'Client', lambda **kwargs: client)
    answer, model = _REAL_COMPLETE('Return JSON', 'Python')
    assert model == 'qwen2.5:3b' and json.loads(answer)['course_ids'] == ['kaggle-python']
    assert observed['format'] == 'json' and observed['stream'] is False
    assert observed['options']['num_predict'] == 300


def test_real_llm_adapter_timeout_is_honest_fallback(monkeypatch):
    import httpx
    monkeypatch.setattr(engine, 'get_model_status', lambda: {'llm_available': True, 'provider': 'ollama'})
    def timeout(request):
        raise httpx.ReadTimeout('local model busy')
    client = httpx.Client(transport=httpx.MockTransport(timeout))
    monkeypatch.setattr(engine.httpx, 'Client', lambda **kwargs: client)
    assert _REAL_COMPLETE('Return JSON', 'Python') == (None, None)
