type ReleaseEnvironment = Record<string, string | undefined>;

export function releaseGitSha(env: ReleaseEnvironment = process.env): string {
  // Deployment-provided identity wins. A project-level override can outlive a
  // deployment and must not make old code look current.
  for (const key of ["VERCEL_GIT_COMMIT_SHA", "GITHUB_SHA", "CAREGIST_RELEASE_SHA"] as const) {
    const candidate = (env[key] ?? "").trim();
    if (/^[0-9a-f]{7,64}$/i.test(candidate)) return candidate.toLowerCase();
  }
  return "unknown";
}
