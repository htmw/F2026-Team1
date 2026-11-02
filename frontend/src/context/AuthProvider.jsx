import { useCallback, useEffect, useMemo, useState } from "react";
import AuthContext from "./AuthContext.js";
import { apiGet, apiPost } from "../services/api.js";

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Ask the backend whether the session cookie is still valid.
  useEffect(() => {
    let ignore = false;

    apiGet("/auth/me")
      .then((me) => {
        if (!ignore) setUser(me);
      })
      .catch(() => {
        if (!ignore) setUser(null);
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const { user: loggedInUser } = await apiPost("/auth/login", {
      email,
      password,
    });
    setUser(loggedInUser);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiPost("/auth/logout");
    } catch {
      // The session is gone either way; clear it locally.
    }
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, logout }),
    [user, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
