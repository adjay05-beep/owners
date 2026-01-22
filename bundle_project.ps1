$source = "d:\owners"
$dest = "d:\owners\project_bundle.zip"
$tempDir = "d:\owners\temp_bundle_v3"

Write-Host "Starting Bundling..."

# 1. Clean
if (Test-Path $dest) { Remove-Item $dest -Force -ErrorAction SilentlyContinue }
if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue }

# 2. Setup
New-Item -Path $tempDir -ItemType Directory | Out-Null
New-Item -Path "$tempDir\frontend" -ItemType Directory | Out-Null

# 3. Copy Python & Configs (Explicit List to avoid junk)
$filesToCopy = @(
    "api.py", "auth.py", "constant.py", "constants.py", "database.py", "services.py", "utils.py", "main.py",
    "requirements.txt", "replit.nix", ".replit", "start.sh"
)

foreach ($file in $filesToCopy) {
    if (Test-Path "$source\$file") {
        Copy-Item -Path "$source\$file" -Destination $tempDir
    }
}

# 4. Copy Frontend (Source Only - No node_modules, no .next)
# We copy specific folders to be safe
Copy-Item -Path "$source\frontend\app" -Destination "$tempDir\frontend\app" -Recurse
if (Test-Path "$source\frontend\public") { Copy-Item -Path "$source\frontend\public" -Destination "$tempDir\frontend\public" -Recurse }

# Copy Frontend Configs
$frontendConfigs = @("package.json", "package-lock.json", "next.config.ts", "tsconfig.json", "postcss.config.mjs", "theme.ts", "eslint.config.mjs", "next-env.d.ts")
foreach ($file in $frontendConfigs) {
    if (Test-Path "$source\frontend\$file") {
        Copy-Item -Path "$source\frontend\$file" -Destination "$tempDir\frontend"
    }
}

# 5. Zip
Compress-Archive -Path "$tempDir\*" -DestinationPath $dest -Force

# 6. Clean
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "SUCCESS: Bundle created at: $dest"
if (Test-Path $dest) {
   $s = (Get-Item $dest).Length / 1KB
   Write-Host "Size: $s KB"
}
