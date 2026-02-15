# Release Checklist

This checklist ensures consistent, high-quality releases of ClawChat. Follow these steps for every release.

## Release Types

- **Major Release** (X.0.0): Breaking changes, major features
- **Minor Release** (0.X.0): New features, backward compatible
- **Patch Release** (0.0.X): Bug fixes, security patches
- **Pre-release** (X.Y.Z-alpha/beta/rc): Testing releases

## Timeline

### 2 Weeks Before Release
- [ ] Plan release scope and features
- [ ] Assign release manager
- [ ] Freeze feature additions
- [ ] Begin release candidate testing

### 1 Week Before Release
- [ ] Complete all planned features
- [ ] Fix critical bugs
- [ ] Create release branch
- [ ] Begin documentation updates

### Release Day
- [ ] Final testing and verification
- [ ] Create release artifacts
- [ ] Publish release
- [ ] Announce release

## Pre-Release Preparation

### Code Quality
- [ ] Run full test suite: `./run_tests.sh ci`
- [ ] Ensure test coverage ≥ 80%
- [ ] Fix all linting errors
- [ ] Resolve all TODO/FIXME comments
- [ ] Update type hints and documentation

### Security
- [ ] Run security scans: `./scripts/security-scan.sh`
- [ ] Check for vulnerable dependencies: `safety check`
- [ ] Verify no secrets in code
- [ ] Review security-related changes
- [ ] Update security documentation if needed

### Documentation
- [ ] Update README.md with new features
- [ ] Update API documentation
- [ ] Update installation instructions
- [ ] Update upgrade guides
- [ ] Verify all links work

### Version Management
- [ ] Update version in `pyproject.toml` or `setup.py`
- [ ] Update version in frontend `package.json` (if applicable)
- [ ] Update version in Dockerfiles
- [ ] Update version in documentation

## Release Candidate (RC) Process

### Create Release Branch
```bash
git checkout develop
git pull origin develop
git checkout -b release/vX.Y.Z-rc1
```

### Update Changelog
- [ ] Add new version section to CHANGELOG.md
- [ ] Include all changes since last release
- [ ] Group changes by type (Added, Changed, Fixed, etc.)
- [ ] Include issue/PR references
- [ ] Highlight breaking changes
- [ ] Note security updates

### Build and Test
- [ ] Build release artifacts
- [ ] Run integration tests
- [ ] Test installation from scratch
- [ ] Test upgrade from previous version
- [ ] Verify all features work

### Create Release Candidate
```bash
git add .
git commit -m "chore: prepare vX.Y.Z-rc1 release"
git tag vX.Y.Z-rc1
git push origin release/vX.Y.Z-rc1
git push origin vX.Y.Z-rc1
```

## Final Release

### Final Verification
- [ ] Test on multiple platforms (Linux, Windows, macOS)
- [ ] Test with different Python versions
- [ ] Verify backward compatibility
- [ ] Test performance benchmarks
- [ ] Verify security features

### Create Release Artifacts
- [ ] Source code archive (.tar.gz)
- [ ] Docker image
- [ ] Python package (wheel)
- [ ] Documentation bundle
- [ ] Release notes

### Sign Release (Optional)
- [ ] Sign Git tag with GPG
- [ ] Sign release artifacts
- [ ] Verify signatures

### Create Final Release
```bash
# Merge to main
git checkout main
git merge --no-ff release/vX.Y.Z
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main
git push origin vX.Y.Z

# Merge to develop
git checkout develop
git merge --no-ff release/vX.Y.Z
git push origin develop
```

## GitHub Release

### Create Release on GitHub
- [ ] Go to GitHub Releases page
- [ ] Click "Draft a new release"
- [ ] Select tag: `vX.Y.Z`
- [ ] Title: "ClawChat vX.Y.Z"
- [ ] Copy changelog content
- [ ] Upload release artifacts
- [ ] Mark as latest release
- [ ] Publish release

### Release Artifacts to Include
- [ ] Source code (zip)
- [ ] Source code (tar.gz)
- [ ] Docker image tags
- [ ] Python package
- [ ] Checksums (SHA256)
- [ ] Signature files

## Post-Release Tasks

### Documentation
- [ ] Update documentation website
- [ ] Update API documentation
- [ ] Update examples and tutorials
- [ ] Announce on project blog

### Distribution
- [ ] Push to PyPI (if applicable)
- [ ] Push Docker image to registry
- [ ] Update package managers (if applicable)
- [ ] Update homebrew formula (if applicable)

### Communication
- [ ] Send release announcement email
- [ ] Post on social media
- [ ] Update community channels
- [ ] Update status page

### Monitoring
- [ ] Monitor error logs
- [ ] Watch for issue reports
- [ ] Track download statistics
- [ ] Monitor performance metrics

## Emergency Release Process

For critical security fixes:

### Immediate Actions
1. **Assess Severity**: Determine impact and urgency
2. **Create Hotfix Branch**: From affected version
3. **Develop Fix**: Minimal changes to address issue
4. **Test Thoroughly**: Focus on security fix
5. **Release Immediately**: Skip non-critical steps

### Communication
- [ ] Notify security team immediately
- [ ] Prepare security advisory
- [ ] Coordinate disclosure timeline
- [ ] Notify affected users

## Rollback Plan

### When to Rollback
- Critical bugs discovered post-release
- Security vulnerabilities in release
- Performance regressions
- Compatibility issues

### Rollback Procedure
1. **Identify Issue**: Document problem and impact
2. **Communicate**: Notify users of rollback
3. **Revert Release**: Mark previous version as latest
4. **Fix Issue**: Develop fix in separate branch
5. **Re-release**: Follow normal release process

## Quality Metrics

### Release Quality Gates
- [ ] Test coverage ≥ 80%
- [ ] No critical security vulnerabilities
- [ ] All automated tests pass
- [ ] Documentation complete
- [ ] Performance within acceptable range
- [ ] Backward compatibility maintained

### Success Metrics
- [ ] Zero critical bugs in first 24 hours
- [ ] Successful upgrades ≥ 95%
- [ ] Positive user feedback
- [ ] No security incidents

## Templates

### Release Announcement Template
```
Subject: ClawChat vX.Y.Z Released!

We're excited to announce ClawChat vX.Y.Z!

## What's New
- Feature 1
- Feature 2
- Security updates

## Breaking Changes
- List any breaking changes

## Upgrade Instructions
[Link to upgrade guide]

## Download
[Link to release page]

## Full Changelog
[Link to CHANGELOG.md]

Thank you to all contributors!
```

### Security Advisory Template
```
## Security Advisory: CVE-YYYY-XXXXX

### Summary
Brief description of vulnerability

### Affected Versions
- ClawChat vX.Y.Z and earlier

### Impact
Description of potential impact

### Solution
Upgrade to vX.Y.Z+1 or apply patch

### Credits
Credit to reporter

### References
- CVE link
- Fix commit
```

## Responsibilities

### Release Manager
- Coordinates release process
- Ensures checklist completion
- Communicates with team
- Makes final release decisions

### Development Team
- Complete feature development
- Fix bugs
- Write tests
- Update documentation

### QA Team
- Test release candidates
- Verify fixes
- Performance testing
- Security testing

### Documentation Team
- Update user guides
- Update API docs
- Write release notes
- Update website

## Tools

### Release Scripts
- `./scripts/prepare-release.sh` - Prepare release artifacts
- `./scripts/verify-release.sh` - Verify release quality
- `./scripts/publish-release.sh` - Publish release

### Monitoring Tools
- Error tracking system
- Performance monitoring
- Security scanning
- User feedback collection

## Continuous Improvement

After each release:
- [ ] Conduct retrospective meeting
- [ ] Document lessons learned
- [ ] Update release process
- [ ] Improve automation
- [ ] Update this checklist

---

**Last Updated**: February 14, 2026  
**Release Manager**: [Name]  
**Next Release**: vX.Y.Z (Target Date: YYYY-MM-DD)