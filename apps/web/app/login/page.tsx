"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, login } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      await login(username, password);
      router.push("/submit");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Sign in failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="auth-shell">
      <form className="auth-panel" onSubmit={submit}>
        <div>
          <h1>Video-to-Note</h1>
          <p>Sign in to create and review session notes.</p>
        </div>

        <label>
          Username
          <input
            autoComplete="username"
            name="username"
            onChange={(event) => setUsername(event.target.value)}
            required
            type="text"
            value={username}
          />
        </label>

        <label>
          Password
          <input
            autoComplete="current-password"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>

        {error ? <p role="alert">{error}</p> : null}

        <button disabled={pending} type="submit">
          {pending ? "Signing in" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
