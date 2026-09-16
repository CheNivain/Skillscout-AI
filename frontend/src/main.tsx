import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
// The bundler handles this stylesheet import; TypeScript has no CSS module declaration.
// @ts-expect-error TS cannot resolve side-effect CSS imports in this configuration.
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
