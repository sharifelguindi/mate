# CI/CD Environment Mapping Analysis

## Current Situation

### Branch to Environment Mapping (in CI/CD pipeline)
```yaml
# From .github/workflows/ci-cd.yml lines 218-287
main branch    → "production" environment
staging branch → "dev" environment  # ⚠️ Confusing!
dev branch     → "dev" environment
```

### Infrastructure Reality
- Only `mate-dev` ECS cluster exists
- No `mate-staging` or `mate-production` clusters created yet
- Demo tenant is deployed to `mate-dev` cluster

## Issues

1. **Naming Confusion**: The `staging` branch deploys to `dev` environment, not a staging environment
2. **No True Staging**: There's no separate staging infrastructure
3. **Demo Tenant Placement**: Demo tenant is in dev, but should ideally be in staging

## Recommended Solution

### Option 1: Fix CI/CD Mapping (Recommended)
```yaml
# Proposed mapping
main branch    → "production" environment
staging branch → "staging" environment  # Fix this
dev branch     → "dev" environment
```

**Required Changes:**
1. Create `mate-staging` ECS cluster in base infrastructure
2. Update CI/CD pipeline line 285 to map staging → staging
3. Deploy demo tenant to staging cluster
4. Keep dev cluster for actual development tenants

### Option 2: Rename Branches
```yaml
# Alternative approach
main branch       → "production" 
development branch → "dev"
# Remove staging branch entirely
```

**Pros:** Simpler, matches current infrastructure
**Cons:** No staging environment for testing before production

### Option 3: Keep As-Is but Document
- Accept that "staging" branch is misnamed
- Document that it's actually another dev environment
- Create separate tenants: `demo` for staging testing, `dev` for development

## Implementation Steps for Option 1

1. **Update Base Infrastructure**
   ```hcl
   # In base/main.tf, add staging cluster
   module "ecs_cluster_staging" {
     source = "./modules/ecs-cluster"
     environment = "staging"
     # ...
   }
   ```

2. **Fix CI/CD Pipeline**
   ```yaml
   # Line 285 in .github/workflows/ci-cd.yml
   elif [[ "$GITHUB_REF" == "refs/heads/staging" ]]; then
     echo "environment=staging" >> $GITHUB_OUTPUT  # Changed from "dev"
   ```

3. **Update Demo Tenant**
   ```hcl
   # In tenants/demo/terraform.tfvars
   environment = "staging"  # Changed from "dev"
   ```

## Current Workaround

For now, the demo tenant is deployed to the `dev` environment because:
- That's the only cluster that exists
- The CI/CD pipeline expects this mapping
- It works, even if the naming is confusing

## Decision Required

Please decide which option to implement:
- [ ] Option 1: Create proper staging infrastructure
- [ ] Option 2: Simplify to just dev and production
- [ ] Option 3: Keep current setup but improve documentation

## Notes

- The confusion likely arose because someone wanted a staging branch but didn't create corresponding infrastructure
- This is a common pattern where git branches don't perfectly map to deployment environments
- The fix is straightforward but requires coordinated changes to infrastructure and CI/CD