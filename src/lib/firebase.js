import { initializeApp } from 'firebase/app';
import {
  GoogleAuthProvider,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut
} from 'firebase/auth';
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  getFirestore,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  writeBatch
} from 'firebase/firestore';

const DEFAULT_FIREBASE_CONFIG = {
  apiKey: 'AIzaSyAMGa-MaCDXaSHoVWSXOb3MUY7DDbT6WMg',
  authDomain: 'hermes-180cd.firebaseapp.com',
  projectId: 'hermes-180cd',
  storageBucket: 'hermes-180cd.firebasestorage.app',
  messagingSenderId: '513112904988',
  appId: '1:513112904988:web:8cdd5cb2d11a33bb1b56d9'
};

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || DEFAULT_FIREBASE_CONFIG.apiKey,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || DEFAULT_FIREBASE_CONFIG.authDomain,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || DEFAULT_FIREBASE_CONFIG.projectId,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || DEFAULT_FIREBASE_CONFIG.storageBucket,
  messagingSenderId:
    import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || DEFAULT_FIREBASE_CONFIG.messagingSenderId,
  appId: import.meta.env.VITE_FIREBASE_APP_ID || DEFAULT_FIREBASE_CONFIG.appId
};

export const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
export const db = getFirestore(firebaseApp);
export const googleProvider = new GoogleAuthProvider();

googleProvider.setCustomParameters({
  prompt: 'select_account'
});

export function subscribeToAuthState(callback) {
  return onAuthStateChanged(auth, callback);
}

export async function signInWithGoogle() {
  try {
    return await signInWithPopup(auth, googleProvider);
  } catch (error) {
    if (error?.code === 'auth/popup-blocked') {
      await signInWithRedirect(auth, googleProvider);
      return null;
    }
    throw error;
  }
}

export function signOutUser() {
  return signOut(auth);
}

export async function getAccessRecord(uid) {
  const snapshot = await getDoc(doc(db, 'access', uid));
  return snapshot.exists() ? snapshot.data() : null;
}

export function subscribeToBriefings(callback, onError) {
  return onSnapshot(
    query(collection(db, 'briefings'), orderBy('id', 'desc')),
    (snapshot) => {
      callback(snapshot.docs.map((item) => item.data()));
    },
    onError
  );
}

export function subscribeToSyntheses(callback, onError) {
  return onSnapshot(
    query(collection(db, 'syntheses'), orderBy('id', 'desc')),
    (snapshot) => {
      callback(snapshot.docs.map((item) => item.data()));
    },
    onError
  );
}

export async function upsertBriefings(briefings, user) {
  const batch = writeBatch(db);

  briefings.forEach((briefing) => {
    const ref = doc(db, 'briefings', briefing.id);
    batch.set(ref, {
      ...briefing,
      updatedAt: serverTimestamp(),
      updatedBy: user.uid
    });
  });

  await batch.commit();
}

export async function upsertSynthesis(synthesis, user) {
  await setDoc(doc(db, 'syntheses', synthesis.id), {
    ...synthesis,
    updatedAt: serverTimestamp(),
    updatedBy: user.uid
  });
}

export function subscribeToAmplifiers(callback, onError) {
  return onSnapshot(
    query(collection(db, 'amplifiers'), orderBy('id', 'desc')),
    (snapshot) => {
      callback(snapshot.docs.map((item) => item.data()));
    },
    onError
  );
}

export async function upsertAmplifier(amplifier, user) {
  await setDoc(doc(db, 'amplifiers', amplifier.id), {
    ...amplifier,
    updatedAt: serverTimestamp(),
    updatedBy: user.uid
  });
}

export async function deleteBriefing(briefingId) {
  await deleteDoc(doc(db, 'briefings', briefingId));
}

export async function clearSharedContent() {
  const [briefingsSnapshot, synthesesSnapshot] = await Promise.all([
    getDocs(collection(db, 'briefings')),
    getDocs(collection(db, 'syntheses'))
  ]);

  const batch = writeBatch(db);

  briefingsSnapshot.forEach((item) => {
    batch.delete(item.ref);
  });

  synthesesSnapshot.forEach((item) => {
    batch.delete(item.ref);
  });

  await batch.commit();
}
