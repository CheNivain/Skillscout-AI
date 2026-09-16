"""Small, explicit domain vocabulary. These are project mappings, not labor-market facts."""
import re

SKILL_ALIASES = {
    "Python": ["python", "python programming"],
    "SQL": ["sql", "structured query language", "postgresql", "mysql"],
    "Excel": ["excel", "spreadsheets"],
    "Power BI": ["power bi", "powerbi"],
    "Statistics": ["statistics", "statistical", "probability"],
    "Machine Learning": ["machine learning", "ml", "scikit-learn", "scikit learn"],
    "Data Visualization": ["data visualization", "data visualisation", "matplotlib", "seaborn"],
    "Pandas": ["pandas", "data wrangling"],
    "Deep Learning": ["deep learning", "neural networks", "tensorflow", "pytorch"],
    "NLP": ["nlp", "natural language processing"],
    "Generative AI": ["generative ai", "genai", "large language models", "llm", "rag"],
    "Artificial Intelligence": ["artificial intelligence", "ai fundamentals", "azure ai"],
    "MLOps": ["mlops", "ml operations", "model deployment"],
    "Data Engineering": ["data engineering", "etl", "data pipelines"],
    "Apache Spark": ["apache spark", "pyspark", "spark"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "React": ["react", "reactjs", "react.js"],
    "HTML & CSS": ["html", "css", "html5", "css3"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "APIs": ["apis", "api", "rest", "restful"],
    "Git": ["git", "github", "version control"],
    "Software Testing": ["software testing", "unit testing", "test automation", "pytest", "jest"],
    "Algorithms": ["algorithms", "data structures"],
    "System Design": ["system design", "software architecture", "distributed systems"],
    "Docker": ["docker", "containers", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Linux": ["linux", "bash", "shell scripting"],
    "AWS": ["aws", "amazon web services", "cloud practitioner"],
    "Azure": ["azure", "az-900", "azure fundamentals"],
    "Cloud Computing": ["cloud computing", "cloud infrastructure", "cloud concepts"],
    "Terraform": ["terraform", "infrastructure as code"],
    "CI/CD": ["ci/cd", "continuous integration", "continuous delivery", "github actions"],
    "Cybersecurity": ["cybersecurity", "cyber security", "information security", "security fundamentals"],
    "Networking": ["networking", "tcp/ip", "network security", "computer networks"],
    "Threat Detection": ["threat detection", "incident response", "siem", "soc analyst"],
    "Secure Coding": ["secure coding", "owasp", "application security", "web security"],
    "Communication": ["communication", "technical writing", "presentation skills"],
    "Agile": ["agile", "scrum"],
    "Project Management": ["project management", "project planning"],
}

ROLE_SKILLS = {
    "data scientist": ["Python", "Statistics", "Machine Learning", "Pandas", "SQL", "Data Visualization"],
    "data analyst": ["SQL", "Excel", "Power BI", "Statistics", "Python", "Data Visualization"],
    "data engineer": ["SQL", "Python", "Data Engineering", "Apache Spark", "Cloud Computing", "Docker"],
    "machine learning engineer": ["Python", "Machine Learning", "Deep Learning", "MLOps", "Docker", "APIs"],
    "ai engineer": ["Python", "Machine Learning", "Generative AI", "NLP", "APIs", "MLOps"],
    "frontend developer": ["HTML & CSS", "JavaScript", "React", "TypeScript", "Git", "Software Testing"],
    "backend developer": ["Python", "SQL", "APIs", "Git", "Software Testing", "Docker", "System Design"],
    "full stack developer": ["JavaScript", "React", "Node.js", "SQL", "APIs", "Git", "Software Testing"],
    "software engineer": ["Python", "Git", "Algorithms", "APIs", "Software Testing", "System Design"],
    "cloud engineer": ["Cloud Computing", "AWS", "Azure", "Linux", "Networking", "Docker", "Terraform"],
    "devops engineer": ["Linux", "Git", "Docker", "CI/CD", "Kubernetes", "Terraform", "Cloud Computing"],
    "cybersecurity analyst": ["Cybersecurity", "Networking", "Linux", "Threat Detection", "Python", "Secure Coding"],
    "security engineer": ["Cybersecurity", "Networking", "Linux", "Threat Detection", "Secure Coding", "Cloud Computing"],
    "qa engineer": ["Software Testing", "Python", "APIs", "Git", "CI/CD"],
    "engineering manager": ["Communication", "Project Management", "Agile", "System Design"],
}

ROLE_ALIASES = {
    "data science": "data scientist", "ml engineer": "machine learning engineer",
    "artificial intelligence engineer": "ai engineer", "front end": "frontend developer",
    "frontend": "frontend developer", "back end": "backend developer", "backend": "backend developer",
    "fullstack": "full stack developer", "full-stack": "full stack developer",
    "software developer": "software engineer", "cloud architect": "cloud engineer",
    "devops": "devops engineer", "security analyst": "cybersecurity analyst",
    "cyber security analyst": "cybersecurity analyst", "quality assurance": "qa engineer",
    "tech lead": "engineering manager",
}

# Project-level pedagogical constraints, independent of provider prerequisites.
PREREQUISITES = {
    "Machine Learning": ["Python", "Statistics"], "Pandas": ["Python"],
    "Deep Learning": ["Python", "Machine Learning"], "NLP": ["Python"],
    "MLOps": ["Python", "Machine Learning", "Docker"], "React": ["JavaScript"],
    "TypeScript": ["JavaScript"], "Node.js": ["JavaScript"],
    "Kubernetes": ["Docker", "Linux"], "Terraform": ["Cloud Computing"],
    "Apache Spark": ["Python", "SQL"], "Threat Detection": ["Cybersecurity", "Networking"],
}

def extract_skills(text: str) -> list[str]:
    """Case-insensitive dictionary NER with boundaries; a skill appears once per document."""
    text = str(text).lower()
    return [skill for skill, aliases in SKILL_ALIASES.items()
            if any(re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", text)
                   for alias in aliases)]

def canonical_skills(items) -> list[str]:
    result = []
    for item in items or []:
        for skill in extract_skills(str(item)):
            if skill not in result:
                result.append(skill)
    return result

def role_targets(text: str) -> list[str]:
    value = str(text).lower()
    for role in sorted(ROLE_SKILLS, key=len, reverse=True):
        if role in value:
            return ROLE_SKILLS[role][:]
    for alias in sorted(ROLE_ALIASES, key=len, reverse=True):
        if alias in value:
            return ROLE_SKILLS[ROLE_ALIASES[alias]][:]
    return []


LEARNING_ENTITIES = {
    "certification": ["Azure AI Fundamentals", "Azure Fundamentals", "AWS Cloud Practitioner",
                      "Google Cybersecurity Professional Certificate"],
    "course": ["Python for Data Science, AI & Development", "Machine Learning Specialization",
               "React Foundations", "Full Stack Open", "Introduction to Cybersecurity"],
    "provider": ["Microsoft Learn", "Kaggle", "Coursera", "AWS", "Cisco", "Google", "GitHub"],
}


def extract_learning_entities(text: str) -> dict[str, list[str]]:
    """Auditable dictionary NER; no claim of a trained statistical NER model."""
    result = {"skill": extract_skills(text)}
    for kind, vocabulary in LEARNING_ENTITIES.items():
        result[kind] = [value for value in vocabulary
                        if re.search(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])", text, re.I)]
    return result
