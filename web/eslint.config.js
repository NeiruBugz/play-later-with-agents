// @ts-check

import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';

export default tseslint.config(
  {
    // Global ignores
    ignores: ['dist', 'node_modules'],
  },
  // Base configurations
  js.configs.recommended,
  ...tseslint.configs.recommended,

  // Configuration for React files (TSX/JSX)
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: {
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    languageOptions: {
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'react/react-in-jsx-scope': 'off', // Not needed with modern React
      'react-refresh/only-export-components': 'warn',
    },
    settings: {
      react: {
        version: 'detect', // Automatically detect the React version
      },
    },
  }
);
