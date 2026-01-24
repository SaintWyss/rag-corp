export type LoginResult = { ok: true } | { ok: false; error: string };

export async function login(email: string, password: string): Promise<LoginResult> {
    const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
        // backend usa RFC7807 application/problem+json
        try {
            const data = await res.json();
            return { ok: false, error: data?.detail ?? "Login failed" };
        } catch {
            return { ok: false, error: "Login failed" };
        }
    }

    return { ok: true };
}
