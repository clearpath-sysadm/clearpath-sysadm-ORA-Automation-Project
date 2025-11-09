# [Feature Name] - Execution Checklist

**Action Plan:** `docs/[FEATURE-NAME]-ACTION-PLAN-V2.md`  
**Created:** [Date]  
**Estimated Total Time:** [X hours] (from action plan Section 6)  
**Status:** Not Started

---

## Pre-Implementation Review

**Before writing any code, complete this review:**

### ✅ Action Plan Verification
- [ ] Read full action plan (all 7 sections)
- [ ] Understand gap analysis decisions (Section 3)
- [ ] Review optimization trade-offs (Section 4)
- [ ] Identify top 3 risks (Section 5)
- [ ] Read deployment process (Section 6)

### ✅ Codebase Preparation
- [ ] Pull latest code from repository
- [ ] Verify all required imports exist (check Section 2.2)
- [ ] Verify all file paths are correct (check Section 2.1)
- [ ] Read `design_guidelines.md` (if frontend)
- [ ] Read `replit.md` for project context

### ✅ Development Environment
- [ ] Install any new dependencies (from Section 2.2)
- [ ] Verify required secrets available (from action plan)
- [ ] Ensure development server running
- [ ] Open relevant files in editor

### ✅ Strategic Planning
- [ ] **Optional:** Review implementation sequence with architect
- [ ] **Optional:** Ask architect to identify potential pitfalls
- [ ] Create git branch for this feature (recommended)

**Estimated Time:** 5-10 minutes

---

## Phase 1: Setup & Foundation

**Goal:** Prepare the technical foundation without breaking anything

**Reference:** Action Plan Section 2.1 (File Structure), Section 2.2 (Technology Stack)

### Create New Files
Copy file list from Section 2.1:

- [ ] Create `[file-path-1]`
- [ ] Create `[file-path-2]`
- [ ] Create `[file-path-3]`

**Tip:** Create empty files first, verify paths are correct

### Stub Core Component/Module
- [ ] Create basic component/module structure
- [ ] Add TypeScript interfaces/types (from Section 2.3)
- [ ] Add placeholder JSDoc comments
- [ ] Verify file imports successfully (no errors)

### Add data-testid Attributes Planning
- [ ] Review action plan for interactive elements
- [ ] Plan data-testid naming convention
- [ ] Document testid list for reference

**Quality Check:**
- [ ] All new files created without errors
- [ ] TypeScript compilation successful
- [ ] No import/path errors in editor
- [ ] Git status shows only intended new files

**Estimated Time:** [X minutes from action plan]

---

## Phase 2: Core Implementation

**Goal:** Build the primary functionality described in Section 1

**Reference:** Action Plan Section 1 (Requirements), Section 2.3-2.6 (Implementation Details)

### Frontend Components (if applicable)
- [ ] Implement main component structure
- [ ] Add form handling (React Hook Form + Zod)
- [ ] Implement core business logic
- [ ] Add loading/error states
- [ ] Add data-testid to all interactive elements
- [ ] Add data-testid to all display elements

### Backend Routes/API (if applicable)
- [ ] Implement API endpoints (from Section 2.7)
- [ ] Add request validation (Zod schemas)
- [ ] Add error handling
- [ ] Add authentication/authorization checks
- [ ] Add logging for debugging

### Database Changes (if applicable)
- [ ] Review schema changes (from Section 2.8)
- [ ] Update Drizzle schema files
- [ ] Run `npm run db:push --force` (never manual migrations)
- [ ] Verify schema changes applied
- [ ] Test with sample data

### State Management
- [ ] Implement local state (useState, useReducer)
- [ ] Add TanStack Query hooks (if server data)
- [ ] Implement optimistic updates (if applicable)
- [ ] Add cache invalidation logic

### Styling & UI/UX
- [ ] Follow design_guidelines.md
- [ ] Apply Tailwind classes (with dark mode variants)
- [ ] Add responsive breakpoints (mobile/tablet/desktop)
- [ ] Implement loading skeletons
- [ ] Add smooth transitions/animations

**Quality Check:**
- [ ] Core functionality works in isolation
- [ ] All TypeScript types correct
- [ ] No console errors
- [ ] Follows existing code patterns
- [ ] Dark mode tested
- [ ] Mobile responsive tested

**Estimated Time:** [X minutes from action plan]

---

## Phase 3: Integration

**Goal:** Connect the feature to the existing application

**Reference:** Action Plan Section 3.5 (Integration Points)

### Routing Integration
Copy from Section 2.1 (Modified Files):

- [ ] Update `client/src/App.tsx` (add import + route)
- [ ] Verify route path matches action plan
- [ ] Test route navigation (no 404 errors)

### Navigation Integration
- [ ] Update navigation menu/sidebar
- [ ] Add links to new feature
- [ ] Verify active state styling
- [ ] Test navigation from all entry points

### Component Integration
- [ ] Import and use shared components
- [ ] Verify props passed correctly
- [ ] Test component interactions
- [ ] Verify no prop type errors

### API Integration (if applicable)
- [ ] Connect frontend to backend endpoints
- [ ] Test request/response flow
- [ ] Verify error handling works
- [ ] Test with network failures (offline mode)

### Data Flow Integration
- [ ] Verify cache invalidation triggers
- [ ] Test optimistic updates
- [ ] Verify loading states show/hide correctly
- [ ] Test pagination/infinite scroll (if applicable)

**Quality Check:**
- [ ] Feature accessible from main navigation
- [ ] All integration points working
- [ ] No conflicts with existing features
- [ ] Shared components render correctly
- [ ] API calls successful (check Network tab)

**Estimated Time:** [X minutes from action plan]

---

## Phase 4: Testing & Quality Assurance

**Goal:** Validate feature works correctly across all scenarios

**Reference:** Action Plan Section 6.4 (Testing Strategy)

### Manual Testing Checklist
Copy test cases from action plan Section 6.4:

- [ ] **Happy path:** [Describe expected flow]
- [ ] **Error handling:** [Test error scenarios]
- [ ] **Edge cases:** [Test boundary conditions]
- [ ] **Cross-browser:** Chrome, Firefox, Safari
- [ ] **Accessibility:** Keyboard navigation, screen reader

### Device Testing
- [ ] **Mobile:** < 768px (Chrome DevTools)
- [ ] **Tablet:** 768px - 1024px
- [ ] **Desktop:** > 1024px
- [ ] **Touch interactions:** Tap targets 44x44px minimum

### Dark Mode Testing
- [ ] Toggle dark mode (verify all colors)
- [ ] Check text contrast (readability)
- [ ] Verify icons/images adapt
- [ ] Test loading states in both modes

### Data Validation Testing
- [ ] Test with empty inputs
- [ ] Test with invalid inputs
- [ ] Test with maximum length inputs
- [ ] Test with special characters
- [ ] Test with XSS attempts (if user input)

### E2E Testing (Playwright)
- [ ] **Decision:** Should this feature have E2E tests? (See action plan Section 6.4)
- [ ] If YES: Create test plan with architect
- [ ] If YES: Run `run_test` tool with test plan
- [ ] If NO: Document why (pure static, no user interaction, etc.)

**Quality Check:**
- [ ] All manual tests passing
- [ ] All devices tested
- [ ] Dark mode works correctly
- [ ] No console errors/warnings
- [ ] Accessibility validated (keyboard + ARIA)

**Estimated Time:** [X minutes from action plan]

---

## Phase 5: Risk Mitigation Verification

**Goal:** Ensure all identified risks have been mitigated

**Reference:** Action Plan Section 5 (Risk Assessment)

### Review Top 3 Risks
Copy from action plan Section 5 (Top 3 Risks):

#### Risk #1: [Risk Name]
- [ ] **Mitigation implemented:** [What was done]
- [ ] **Verification test:** [How to verify mitigation works]
- [ ] **Result:** PASS / FAIL

#### Risk #2: [Risk Name]
- [ ] **Mitigation implemented:** [What was done]
- [ ] **Verification test:** [How to verify mitigation works]
- [ ] **Result:** PASS / FAIL

#### Risk #3: [Risk Name]
- [ ] **Mitigation implemented:** [What was done]
- [ ] **Verification test:** [How to verify mitigation works]
- [ ] **Result:** PASS / FAIL

### Breaking Changes Check
- [ ] Review Section 5 "Breaking Changes" category
- [ ] Verify backward compatibility maintained
- [ ] Test existing features still work
- [ ] Run regression tests (if available)

### Security Validation
- [ ] Review Section 5 "Security" category
- [ ] Verify input sanitization implemented
- [ ] Check authentication/authorization working
- [ ] Test with malicious inputs
- [ ] Verify secrets not exposed in code/logs

**Quality Check:**
- [ ] All risk mitigations verified
- [ ] No new breaking changes introduced
- [ ] Security measures implemented
- [ ] Rollback plan documented (if high-risk)

**Estimated Time:** [X minutes]

---

## Phase 6: Documentation

**Goal:** Update project documentation so future developers understand changes

**Reference:** Action Plan Section 6.5 (Documentation Updates)

### Code Documentation
- [ ] Add JSDoc comments to complex functions
- [ ] Document any non-obvious logic
- [ ] Add inline comments for "why" not "what"
- [ ] Update component props documentation

### Project Documentation
Copy specific files from action plan Section 6.5:

- [ ] Update `replit.md` with new feature description
- [ ] Update architecture docs (if applicable)
- [ ] Update API documentation (if new endpoints)
- [ ] Update README (if user-facing changes)

### Feature-Specific Documentation
- [ ] Document any configuration options
- [ ] Document any environment variables added
- [ ] Document any new npm scripts
- [ ] Document any deployment requirements

**Quality Check:**
- [ ] All code comments helpful and accurate
- [ ] replit.md reflects new feature
- [ ] No outdated documentation remaining
- [ ] Future developers can understand changes

**Estimated Time:** [X minutes from action plan]

---

## Phase 7: Pre-Deployment Validation

**Goal:** Final checks before marking feature complete

**Reference:** Action Plan Section 6 (Deployment Process)

### Code Quality Review
- [ ] Run TypeScript compiler (`tsc --noEmit`)
- [ ] Fix any type errors
- [ ] Run linter (if configured)
- [ ] Fix linting errors
- [ ] Remove console.logs (except intentional logging)
- [ ] Remove commented-out code

### Performance Check
- [ ] Review bundle size impact (from Section 4.1.1)
- [ ] Verify lazy loading working (if applicable)
- [ ] Check render performance (React DevTools)
- [ ] Verify no memory leaks (Chrome DevTools)
- [ ] Test with slow network (Chrome DevTools throttling)

### Accessibility Final Check
- [ ] All interactive elements have data-testid
- [ ] All images have alt text
- [ ] All forms have labels
- [ ] Color contrast meets WCAG AA standards
- [ ] Keyboard navigation works completely

### Gap Closure Verification
- [ ] Review action plan Section 3.8 (Gap Closure Table)
- [ ] Verify all gaps addressed as documented
- [ ] No new gaps introduced during implementation
- [ ] Deferred features documented for future

**Quality Check:**
- [ ] No TypeScript errors
- [ ] No console errors/warnings
- [ ] Performance meets action plan targets
- [ ] Accessibility standards met
- [ ] All gaps addressed

**Estimated Time:** [X minutes]

---

## Phase 8: Deployment & Verification

**Goal:** Launch feature and verify it works in production

**Reference:** Action Plan Section 6.6 (Post-Deployment Verification)

### Deployment Steps
- [ ] Commit all changes with descriptive message
- [ ] Push to repository
- [ ] Restart workflow (if needed)
- [ ] Verify workflow starts without errors
- [ ] Wait for successful deployment

### Production Verification
Copy from action plan Section 6.6:

- [ ] Verify route accessible in production
- [ ] Test core functionality in production
- [ ] Verify data persistence (if applicable)
- [ ] Check browser console for errors
- [ ] Verify analytics tracking (if applicable)

### Smoke Testing
- [ ] Test happy path end-to-end
- [ ] Verify no 500 errors in logs
- [ ] Verify no database errors
- [ ] Test on real mobile device (if possible)
- [ ] Share with 1-2 beta users (optional)

### Rollback Readiness
- [ ] Document current commit hash
- [ ] Verify rollback process (from Section 5)
- [ ] Know how to quickly revert if needed
- [ ] Monitor for 15-30 minutes post-launch

**Quality Check:**
- [ ] Feature live in production
- [ ] No errors in production logs
- [ ] Smoke tests passing
- [ ] Rollback plan ready if needed

**Estimated Time:** [X minutes from action plan]

---

## Post-Implementation Review

**After successful deployment:**

### Architect Code Review
- [ ] Call architect tool with git diff
- [ ] Review architect feedback
- [ ] Address any critical issues found
- [ ] Document any improvements for next feature

### Update Action Plan Status
- [ ] Mark action plan as "Implemented"
- [ ] Document actual time vs estimated time
- [ ] Note any deviations from plan
- [ ] Document lessons learned

### Metrics Tracking (Optional)
- [ ] Measure bundle size impact (actual vs estimated)
- [ ] Measure initial page load time
- [ ] Track user engagement (if analytics setup)
- [ ] Monitor error rates

### Celebration 🎉
- [ ] Feature successfully launched!
- [ ] Mark task list as complete
- [ ] Share success with team (if applicable)
- [ ] Move to next feature

**Estimated Time:** 10-15 minutes

---

## Execution Summary

| Phase | Estimated Time | Actual Time | Status | Notes |
|-------|----------------|-------------|--------|-------|
| Pre-Implementation | [X] min | | ⏸️ | |
| Phase 1: Setup | [X] min | | ⏸️ | |
| Phase 2: Core | [X] min | | ⏸️ | |
| Phase 3: Integration | [X] min | | ⏸️ | |
| Phase 4: Testing | [X] min | | ⏸️ | |
| Phase 5: Risk Mitigation | [X] min | | ⏸️ | |
| Phase 6: Documentation | [X] min | | ⏸️ | |
| Phase 7: Pre-Deployment | [X] min | | ⏸️ | |
| Phase 8: Deployment | [X] min | | ⏸️ | |
| **Total** | **[X] hours** | | | |

**Status Legend:** ⏸️ Not Started | 🔄 In Progress | ✅ Complete | ❌ Blocked

---

## Quick Tips for Success

### ✅ DO:
- Read the full action plan before coding
- Test as you build (don't batch at end)
- Follow existing code patterns
- Add data-testid to all interactive elements
- Check dark mode after every UI change
- Commit frequently with good messages
- Ask architect for help when stuck

### ❌ DON'T:
- Skip the pre-implementation review
- Deviate from action plan without reason
- Batch all testing until the end
- Forget mobile/tablet testing
- Skip accessibility checks
- Write manual SQL migrations (use db:push)
- Rush the risk mitigation phase

---

## Troubleshooting

### If Implementation Taking Longer Than Estimated:
1. Review action plan optimization section (Section 4)
2. Identify which phase is slower than expected
3. Check if scope creep occurred
4. Consider deferring nice-to-have features
5. Ask architect for optimization suggestions

### If Tests Failing:
1. Review action plan Section 6.4 (Testing Strategy)
2. Check if mitigations implemented (Section 5)
3. Verify all integration points (Section 3.5)
4. Test in isolation to identify issue
5. Use browser DevTools for debugging

### If Blocked:
1. Review action plan for guidance
2. Check if gap was identified but not addressed
3. Search codebase for similar patterns
4. Ask architect for strategic guidance
5. Document blocker for user review

---

**This checklist was generated from:** `docs/[FEATURE-NAME]-ACTION-PLAN-V2.md`  
**Last Updated:** [Date]
