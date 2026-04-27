"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signup } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { onLogin } = useAuth();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);

    try {
      await signup({ email, password });
      onLogin();
      router.push("/decks");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Signup failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-xl font-bold text-text-primary">
            <span className="text-accent-green">MTG</span> deck-intelligence
          </h1>
          <p className="text-text-muted text-sm mt-2">
            <span className="text-accent-green">$</span> create new account
          </p>
        </div>

        {/* Form */}
        <div className="panel p-6">
          <div className="text-xs text-text-muted mb-4 font-medium uppercase tracking-wider">
            Sign Up
          </div>

          {error && (
            <div className="mb-4 px-3 py-2 bg-accent-red/10 border border-accent-red/30 rounded text-accent-red text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-terminal"
                placeholder="user@example.com"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-terminal"
                placeholder="min 6 characters"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-text-secondary mb-1.5">
                confirm password
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="input-terminal"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? (
                <span>
                  creating account
                  <span className="animate-pulse">...</span>
                </span>
              ) : (
                "create account →"
              )}
            </button>
          </form>

          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-text-muted text-xs text-center">
              already have an account?{" "}
              <Link
                href="/auth/login"
                className="text-accent-green hover:text-accent-green/80 transition-colors"
              >
                login
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}