
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

// Import CSS files
import './styles/variables.css';
import './styles/global.css';
import './styles/components.css';
import './styles/responsive.css';

// Render React application
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
