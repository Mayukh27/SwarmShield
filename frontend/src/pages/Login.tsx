import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import FloatingLines from "@/components/FloatingLines";

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = (event: React.FormEvent) => {
    event.preventDefault();

    // Frontend demo authentication.
    // Connect this to your real backend later.
    navigate("/dashboard");
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#030508] text-white">

      {/* React Bits background */}
      <div className="absolute inset-0 opacity-60">
        <FloatingLines
          enabledWaves={["top", "middle", "bottom"]}
          lineCount={7}
          lineDistance={6}
          animationSpeed={0.35}
        />
      </div>

      {/* Dark overlay */}
      <div className="absolute inset-0 bg-[#030508]/65" />

      {/* Grid */}
      <div
        className="absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.2) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex min-h-screen items-center justify-center px-5 py-10">

        <div className="w-full max-w-md">

          {/* Logo */}
          <div className="mb-8 text-center">

            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan-400/30 bg-cyan-400/10 shadow-[0_0_40px_rgba(34,211,238,0.12)]">

              <span className="text-xl font-bold text-cyan-300">
                S
              </span>

            </div>

            <h1 className="mt-5 text-2xl font-semibold tracking-[0.18em]">
              SWARMSHIELD
            </h1>

            <p className="mt-2 text-[9px] tracking-[0.35em] text-white/25">
              AUTONOMOUS SECURITY PLATFORM
            </p>

          </div>

          {/* Login card */}
          <div className="glass-dark rounded-3xl p-7 sm:p-8">

            <div className="mb-7">

              <div className="flex items-center gap-2">

                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />

                <span className="text-[9px] tracking-[0.25em] text-cyan-300/70">
                  SECURE ACCESS
                </span>

              </div>

              <h2 className="mt-3 text-xl font-semibold">
                Welcome back
              </h2>

              <p className="mt-2 text-xs leading-relaxed text-white/30">
                Access your autonomous security command center.
              </p>

            </div>

            <form
              onSubmit={handleLogin}
              className="space-y-5"
            >

              {/* Email */}
              <div>

                <label className="mb-2 block text-[10px] tracking-widest text-white/40">
                  EMAIL
                </label>

                <input
                  type="email"
                  required
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  placeholder="operator@swarmshield.io"
                  className="h-12 w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 text-sm text-white outline-none transition placeholder:text-white/15 focus:border-cyan-400/40 focus:bg-cyan-400/[0.02] focus:ring-1 focus:ring-cyan-400/10"
                />

              </div>

              {/* Password */}
              <div>

                <div className="mb-2 flex justify-between">

                  <label className="text-[10px] tracking-widest text-white/40">
                    PASSWORD
                  </label>

                  <button
                    type="button"
                    className="text-[9px] text-cyan-300/50 hover:text-cyan-300"
                  >
                    FORGOT?
                  </button>

                </div>

                <input
                  type="password"
                  required
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  placeholder="••••••••••••"
                  className="h-12 w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 text-sm text-white outline-none transition placeholder:text-white/15 focus:border-cyan-400/40 focus:bg-cyan-400/[0.02] focus:ring-1 focus:ring-cyan-400/10"
                />

              </div>

              {/* Remember */}
              <label className="flex items-center gap-3">

                <input
                  type="checkbox"
                  className="h-4 w-4 accent-cyan-400"
                />

                <span className="text-[10px] text-white/30">
                  Keep me signed in
                </span>

              </label>

              {/* Login */}
              <Button
                type="submit"
                className="h-12 w-full rounded-xl bg-cyan-400 font-semibold text-black shadow-[0_0_25px_rgba(34,211,238,0.12)] transition hover:bg-cyan-300 hover:shadow-[0_0_35px_rgba(34,211,238,0.2)]"
              >
                Enter Command Center
              </Button>

            </form>

            {/* Divider */}
            <div className="my-7 flex items-center gap-4">

              <div className="h-px flex-1 bg-white/5" />

              <span className="text-[8px] tracking-widest text-white/15">
                SECURE CONNECTION
              </span>

              <div className="h-px flex-1 bg-white/5" />

            </div>

            {/* Security status */}
            <div className="rounded-xl border border-emerald-400/10 bg-emerald-400/[0.03] p-4">

              <div className="flex items-center gap-3">

                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400/10">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                </div>

                <div>

                  <p className="text-[10px] font-medium text-emerald-400">
                    SECURITY SYSTEMS ONLINE
                  </p>

                  <p className="mt-1 text-[9px] text-white/20">
                    Autonomous infrastructure ready
                  </p>

                </div>

              </div>

            </div>

          </div>

          <p className="mt-6 text-center text-[9px] text-white/15">
            Autonomous Multi-Agent Security Platform
          </p>

        </div>

      </div>

    </main>
  );
}