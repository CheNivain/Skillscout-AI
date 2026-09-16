import { useState } from 'react';
import type { FormEvent } from 'react';
import {
  ArrowRight,
  ChevronRight,
  Eye,
  EyeOff,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { api, setCsrf } from './api';
import { Brand } from './components';
import type { User } from './types';

export default function Auth({ onLogin }: { onLogin: (user: User) => void }) {
  const [register, setRegister] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [demo, setDemo] = useState('employee');
  async function signIn(event?: FormEvent, demoRole?: string) {
    event?.preventDefault();
    setBusy(true);
    setError('');
    try {
      const demoEmail =
        demoRole === 'employee' ? 'alex@skillscout.demo' : `${demoRole}@skillscout.demo`;
      const data = await api<{ user: User; csrf_token: string }>(
        register && !demoRole ? '/auth/register' : '/auth/login',
        'POST',
        demoRole
          ? { email: demoEmail, password: 'SkillScout123!' }
          : { email, password, ...(register ? { name } : {}) },
      );
      setCsrf(data.csrf_token);
      onLogin(data.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <section className="auth-form-side">
        <div className="auth-mobile-brand">
          <Brand />
        </div>
        <div className="auth-top-note">
          YOUR PRIVATE LEARNING WORKSPACE <ShieldCheck size={15} />
        </div>
        <div className="auth-form-wrap">
          <p className="eyebrow">LET’S MAKE YOUR NEXT MOVE</p>
          <h2>{register ? 'Create an account' : 'Sign in to SkillScout'}</h2>
          <p className="muted">
            {register
              ? 'Set up your employee learning profile.'
              : 'Sign in to manage your training and recommendations.'}
          </p>
          <div className="auth-tabs" role="group" aria-label="Authentication mode">
            <button
              className={!register ? 'active' : ''}
              onClick={() => {
                setRegister(false);
                setError('');
              }}
            >
              Sign in
            </button>
            <button
              className={register ? 'active' : ''}
              onClick={() => {
                setRegister(true);
                setError('');
              }}
            >
              Create account
            </button>
          </div>
          <form onSubmit={(event) => void signIn(event)}>
            {register && (
              <label>
                Full name
                <input
                  autoComplete="name"
                  required
                  maxLength={100}
                  placeholder="Alex Morgan"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
            )}
            <label>
              Email address
              <input
                type="email"
                autoComplete="email"
                required
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Password
              <div className="password-input">
                <input
                  type={show ? 'text' : 'password'}
                  autoComplete={register ? 'new-password' : 'current-password'}
                  required
                  minLength={register ? 10 : 1}
                  maxLength={128}
                  placeholder={register ? 'At least 10 characters' : 'Enter your password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="icon-button"
                  aria-label={show ? 'Hide password' : 'Show password'}
                  onClick={() => setShow(!show)}
                >
                  {show ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </label>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button primary auth-submit" disabled={busy}>
              {busy ? (
                <LoaderCircle size={18} className="spin" />
              ) : (
                <>
                  {register ? 'Create account' : 'Sign in'}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
          <div className="auth-divider">
            <span>Demo accounts</span>
          </div>
          <div className="demo-box">
            <div>
              <Sparkles size={17} />
              <strong>Try the demo</strong>
            </div>
            <p>Choose a role to test the system.</p>
            <div className="demo-role-group" role="group" aria-label="Demo role">
              {['employee', 'hr', 'admin'].map((role) => (
                <button
                  key={role}
                  className={demo === role ? 'active' : ''}
                  onClick={() => setDemo(role)}
                >
                  {role === 'employee' ? 'Employee' : role === 'hr' ? 'HR / L&D' : 'Admin'}
                </button>
              ))}
            </div>
            <button
              className="demo-enter"
              disabled={busy}
              onClick={() => void signIn(undefined, demo)}
            >
              Sign in as {demo === 'employee' ? 'Alex' : demo === 'hr' ? 'Jordan' : 'Sam'}
              <ChevronRight size={17} />
            </button>
          </div>
          <p className="auth-privacy">
            <ShieldCheck size={14} /> Local-first. Your career goals stay in your workspace.
          </p>
        </div>
        <div className="auth-bottom-note">Thoughtful technology for a more intentional career.</div>
      </section>
    </div>
  );
}
