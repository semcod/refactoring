# CI/CD Integration Examples

This directory contains examples for integrating prefact into CI/CD pipelines.

## GitHub Actions

See `.github/workflows/prefact.yml` for a complete GitHub Actions workflow that:
- Runs prefact on pull requests
- Fails if new issues are introduced
- Generates reports as artifacts
- Supports auto-fix with commit

## GitLab CI

See `.gitlab-ci.yml` for GitLab CI configuration that:
- Runs prefact in merge requests
- Creates JSON reports
- Integrates with GitLab's code quality

## Azure DevOps

See `azure-pipelines.yml` for Azure DevOps pipeline.

## Jenkins

See `Jenkinsfile` for Jenkins pipeline configuration.

## Best Practices

1. **Fail Fast**: Configure CI to fail if new issues are detected
2. **Reports**: Save JSON reports as pipeline artifacts
3. **Incremental**: Only check changed files in large projects
4. **Fix Mode**: Use `--dry-run` for reporting, `fix` for automated cleanup
5. **Caching**: Cache dependencies for faster CI runs

## Configuration Tips

- Use project-specific `prefact.yaml` files
- Exclude test directories if needed
- Set appropriate severity levels for CI
- Use JSON output for programmatic processing
