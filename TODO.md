# Connection to https://github.com/z0diax/qr-scanner TODO

## Plan Execution Steps

### 1. Git Operations [IN PROGRESS]
- [ ] `git add .` - Stage all modified/untracked files
- [ ] `git status` - Verify staged changes
- [ ] `git commit -m "Add combined GAS script, installer, sync improvements, docs"` - Commit changes
- [ ] `git push origin main` - Push to upstream repo

### 2. Post-Push Verification
- [ ] Confirm push success (check repo online or git log)
- [ ] Update README.md if needed (reference new features)

### 3. Deployment & Testing
- [ ] Deploy GAS web app per COMBINED_SCRIPT_SETUP.md
- [ ] Configure app with Sheet CSV URL + GAS export URL
- [ ] Test end-to-end sync/export

### 4. Optional
- [ ] Build installer: `installer/build_installer.bat`
- [ ] Test standalone EXE
