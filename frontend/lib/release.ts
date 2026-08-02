type ReleaseEnvironment = Record<string, string | undefined>;

export function releaseGitSha(env: ReleaseEnvironment = process.env): string {
  const candidate = env.CAREGIST_RELEASE_SHA || env.VERCEL_GIT_COMMIT_SHA || env.GITHUB_SHA || "";
  return /^[0-9a-f]{7,64}$/i.test(candidate) ? candidate.toLowerCase() : "unknown";
}
