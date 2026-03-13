import { initializeApp } from 'firebase/app';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'ABC123',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'hermes-180cd.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'hermes-180cd',
  storageBucket:
    import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'hermes-180cd.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '513112904988',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:513112904988:web:8cdd5cb2d11a33bb1b56d9'
};

export const firebaseApp = initializeApp(firebaseConfig);
