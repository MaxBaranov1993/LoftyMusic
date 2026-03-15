"use client";

import { useAuth } from "@clerk/nextjs";
import { createContext, useContext, useEffect, useState } from "react";
import { setTokenGetter } from "@/lib/api";

const AuthReadyContext = createContext(false);

export function useAuthReady() {
  return useContext(AuthReadyContext);
}

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { getToken, isLoaded } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    setTokenGetter(getToken);
    setReady(true);
  }, [getToken, isLoaded]);

  return (
    <AuthReadyContext.Provider value={ready}>
      {children}
    </AuthReadyContext.Provider>
  );
}
