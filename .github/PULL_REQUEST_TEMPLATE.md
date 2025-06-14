# Pull Request

## Description
Brief description of changes made in this PR.

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue) - **PATCH version bump**
- [ ] ✨ New feature (non-breaking change which adds functionality) - **MINOR version bump**
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected) - **MAJOR version bump**
- [ ] 📚 Documentation update - **PATCH version bump**
- [ ] ♻️ Code refactoring - **PATCH version bump**

## Version Bump
When this PR is merged, the version will be automatically bumped based on the type of change in the title:
How It Works:

  For Automatic Releases (Most Common):

  1. Label PR with appropriate title:
    - `patch` - Force patch version bump
    - `minor` - Force minor version bump
    - `major` - Force major version bump
    - `breaking` - Force major version bump
  2. Merge PR → Automatically:
    - Detects version bump type
    - Updates manifest.json
    - Creates git tag
    - Generates release with notes
    - Comments on PR with release URL

## Testing
- [ ] Local testing performed
- [ ] Integration loads successfully in Home Assistant
- [ ] All existing functionality still works
- [ ] New functionality works as expected

## Device Testing
- [ ] Tested with PowerMeter devices
- [ ] Tested with RoomSensor devices
- [ ] Tested with WaterMeter devices
- [ ] Tested with scenario controls

## Validation
- [ ] No API keys or sensitive data in code
- [ ] Code follows existing patterns

## Documentation
- [ ] README updated if needed
- [ ] Code comments added for complex logic
- [ ] Breaking changes documented

## Release Notes
When this PR is merged, a new release will be automatically created. The release notes will include:
- This PR title and description
- Installation instructions
- Supported devices list
- Links to documentation

## Additional Notes
Any additional information about the changes.
