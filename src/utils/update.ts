
import { getVersion } from '@tauri-apps/api/app'

const RELEASE_API =
  'https://api.github.com/repos/meet-fish-code/gugu-pdf-tools/releases/latest'

const RELEASE_PAGE =
  'https://github.com/meet-fish-code/gugu-pdf-tools/releases/latest'

interface GithubRelease {
  tag_name: string
  name: string
  body: string
  html_url: string
  published_at: string
  assets: {
    name: string
    browser_download_url: string
    size: number
  }[]
}

export interface UpdateInfo {
  hasUpdate: boolean
  currentVersion: string
  latestVersion: string
  releaseName: string
  releaseNotes: string
  releaseUrl: string
  publishedAt: string
  downloadUrl: string
}

function compareVersion(a: string, b: string): number {
  const parse = (version: string) =>
    version.replace(/^v/i, '').split('.').map(Number)

  const va = parse(a)
  const vb = parse(b)

  for (let i = 0; i < Math.max(va.length, vb.length); i++) {
    const x = va[i] || 0
    const y = vb[i] || 0

    if (x > y) return 1
    if (x < y) return -1
  }

  return 0
}

export async function checkUpdate(): Promise<UpdateInfo> {
  const currentVersion = await getVersion()

  const response = await fetch(RELEASE_API, {
    headers: {
      Accept: 'application/vnd.github+json',
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })

  if (!response.ok) {
    throw new Error(`获取更新信息失败：HTTP ${response.status}`)
  }

  const release: GithubRelease = await response.json()

  const latestVersion = release.tag_name.replace(/^v/i, '')

  const installer = release.assets.find(asset =>
    asset.name.toLowerCase().endsWith('.exe')
  )

  return {
    hasUpdate: compareVersion(latestVersion, currentVersion) > 0,
    currentVersion,
    latestVersion,
    releaseName: release.name,
    releaseNotes: release.body || '暂无更新说明',
    releaseUrl: release.html_url || RELEASE_PAGE,
    publishedAt: release.published_at,
    downloadUrl: installer?.browser_download_url || release.html_url,
  }
}
