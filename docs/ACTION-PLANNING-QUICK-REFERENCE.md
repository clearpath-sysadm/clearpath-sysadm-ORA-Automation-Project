# Action Planning Quick Reference Card

**Version:** 1.1  
**For:** ClearPath AI Project  
**Purpose:** Fast lookup guide for creating action plans

---

## 🚀 8-Step Workflow at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Requirements (10 mins) → Section 1-2               │
│ ✅ Checklist: Must-have vs nice-to-have separated          │
│ ✅ Checklist: All imports verified in codebase             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Gap Analysis (15 mins) → Section 3                 │
│ ✅ Checklist: 5 context areas analyzed                     │
│ 🔄 Gap Closure Loop: Feed solutions back to Sec 1-2        │
│ ✅ Checklist: Gap closure table complete                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Optimization (10 mins) → Section 4                 │
│ ✅ Checklist: Trade-offs have reasoning                    │
│ ✅ Checklist: Time savings calculated                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Risk Assessment (15 mins) → Section 5              │
│ ✅ Checklist: All 6 risk categories assessed               │
│ ✅ Checklist: Every risk has mitigation                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Deployment (10 mins) → Section 6                   │
│ ✅ Checklist: Time estimates per phase                     │
│ ✅ Checklist: All file paths verified                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Executive Summary (5 mins) → Section 7             │
│ ✅ Checklist: Non-technical description                    │
│ ✅ Checklist: Clear recommendation                         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Final Readiness Review (5 mins) ⭐ NEW              │
│ ✅ All section checklists passed                           │
│ ✅ Final accuracy checklist complete                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 8: Present to User                                    │
│ Share executive summary → Get approval → Implement         │
└─────────────────────────────────────────────────────────────┘

Total Time: 70-80 minutes
```

---

## ✅ Section Checklists (Copy-Paste Ready)

### Section 1: Feature Requirements
```
- [ ] Must-have vs nice-to-have clearly separated
- [ ] Technical specs match existing system patterns
- [ ] Success criteria are measurable
- [ ] No placeholder text or assumptions
- [ ] User benefits clearly articulated
```

### Section 2: Technical Implementation
```
- [ ] All imports verified to exist in codebase
- [ ] Component dependencies are available
- [ ] State management follows existing patterns
- [ ] No assumptions about missing infrastructure
- [ ] File paths are accurate
- [ ] Technology stack items match project
```

### Section 3: Gap Analysis
```
- [ ] All 5 context areas analyzed (frontend, backend, UI/UX, cross-platform, integration)
- [ ] Every gap has solution options with complexity estimates
- [ ] Decision made for each gap with clear reasoning
- [ ] Gap solutions fed back to Sections 1-2 (updates documented)
- [ ] Gap closure summary table complete (all gaps show "Closed" or "Documented")
- [ ] No assumptions or placeholder text
```

### Section 4: Optimization Strategy
```
- [ ] Performance impact quantified (bundle size, render time, etc.)
- [ ] Code quality standards maintained (TypeScript, accessibility, etc.)
- [ ] UX optimizations cover all states (loading, error, empty, success)
- [ ] Trade-offs have clear reasoning (not just lists)
- [ ] Time savings calculated for skipped features
- [ ] Value retention estimated for included features
```

### Section 5: Risk Assessment
```
- [ ] All 6 risk categories assessed (breaking changes, data, UX, performance, security, deployment)
- [ ] Risk matrix complete with likelihood + impact
- [ ] Every risk has mitigation strategy
- [ ] Rollback plan defined for breaking changes
- [ ] Overall risk score calculated
- [ ] High-risk items have contingency plans
```

### Section 6: Deployment Process
```
- [ ] Implementation checklist has time estimates per phase
- [ ] All file paths verified to be correct
- [ ] Integration steps match existing patterns
- [ ] Testing strategy covers manual + E2E where applicable
- [ ] Documentation updates list specific files
- [ ] Post-deployment verification includes rollback triggers
```

### Section 7: Executive Summary
```
- [ ] Description is non-technical (user can understand)
- [ ] Effort estimate broken down by phase
- [ ] Value assessment covers user + business + strategic
- [ ] Top 3 risks listed with mitigation
- [ ] Resource requirements complete (dependencies, secrets, infrastructure)
- [ ] Decision points have clear options
- [ ] Recommendation is clear (YES/NO/MODIFY with reasoning)
```

---

## 🔄 Gap Closure Feedback Loop (Critical!)

**Problem:** Gaps identified in Section 3, but Sections 1-2 don't reflect the solutions.

**Solution:** For each gap, document where you applied the solution:

```
Gap: Pixel Width vs Character Count
Solution: Use 120-160 char range (industry standard)
✅ Applied to Section 1.2: Updated validation rules
✅ Applied to Section 2.6: Updated getValidationStatus function
✅ Applied to Section 4.4: Added to "What We're Skipping"
```

**Gap Closure Table Template:**

| Gap | Solution Chosen | Updates Applied | Status |
|-----|----------------|-----------------|--------|
| [Gap 1] | [Solution] | Sec X.X, Y.Y | ✅ Closed |
| [Gap 2] | [Solution] | Sec X.X | ✅ Closed |
| [Gap 3] | [Solution] | Sec 4.4 (deferred) | ✅ Documented |

---

## 🎯 Final Readiness Review Checklist

**Run this before presenting to user:**

### ✅ Factual Alignment
```
- [ ] All tech stack items exist in project (verify imports)
- [ ] File paths are accurate (no typos)
- [ ] Component dependencies available
- [ ] No assumptions about missing infrastructure
```

### ✅ Dependency Coverage
```
- [ ] All npm packages available or listed as "to install"
- [ ] All integrations identified (APIs, auth, database)
- [ ] Secret requirements documented
- [ ] External services clearly stated
```

### ✅ Risk Mitigation Linkage
```
- [ ] Every risk has mitigation strategy
- [ ] High-impact risks have contingency plans
- [ ] Rollback plan exists for breaking changes
- [ ] Overall risk score calculated
```

### ✅ Design & SEO Compliance
```
- [ ] Matches design_guidelines.md (if frontend)
- [ ] Follows existing UI patterns
- [ ] SEO requirements included (if public-facing)
- [ ] Accessibility standards met
```

### ✅ Document Artifacts
```
- [ ] All referenced files exist
- [ ] Gap closure table complete
- [ ] Section checklists all passed
- [ ] No placeholder text (TODO, TBD, etc.)
- [ ] Time estimates realistic
```

### ✅ Completeness Gate
```
- [ ] All 7 sections present
- [ ] Executive summary created
- [ ] Gap solutions fed back to Sections 1-2
- [ ] Trade-offs have reasoning
- [ ] Decision points clear
```

**If any item fails:** Fix it before presenting to user.

---

## 📋 5 Context Areas for Gap Analysis

When analyzing gaps, always check these 5 areas:

### 1. Frontend Context
- Existing component patterns (shadcn/ui, custom components)
- UI/UX consistency (design system, dark mode, spacing)
- Responsive design (mobile/tablet/desktop)
- Accessibility standards (ARIA labels, keyboard nav)

### 2. Backend Context
- Existing API patterns (Express routes, middleware)
- Database schema compatibility (Drizzle ORM, PostgreSQL)
- Authentication/authorization (Replit Auth)
- Error handling patterns

### 3. UI/UX Consistency
- Design system alignment (colors, typography, spacing)
- Dark mode compatibility
- Component reusability
- Visual hierarchy

### 4. Cross-Platform Considerations
- Mobile responsiveness (< 768px)
- Tablet compatibility (768px - 1024px)
- Desktop layout (> 1024px)
- Touch vs mouse interactions

### 5. Integration Points
- How does this interact with existing features?
- Does it conflict with current functionality?
- What shared components can be reused?
- What new reusable components should be created?

---

## 🚨 Common Pitfalls to Avoid

### ❌ Gap Analysis Mistakes
- **Don't:** Identify gaps but forget to update Sections 1-2
- **Do:** Use gap closure feedback loop + summary table

### ❌ Risk Assessment Mistakes
- **Don't:** Skip risk categories or mitigation strategies
- **Do:** Assess all 6 categories + create risk matrix

### ❌ Optimization Mistakes
- **Don't:** List trade-offs without reasoning
- **Do:** Explain why + calculate time savings

### ❌ Deployment Mistakes
- **Don't:** Give total time only ("30 minutes")
- **Do:** Break down by phase ("15+7+5+3 mins")

### ❌ Executive Summary Mistakes
- **Don't:** Use technical jargon or assume context
- **Do:** Non-technical description user can understand

### ❌ Readiness Review Mistakes
- **Don't:** Skip final accuracy check
- **Do:** Run full checklist before presenting

---

## 📁 File Naming Convention

### Detailed Action Plan:
```
docs/[FEATURE-NAME]-ACTION-PLAN-V2.md
```

Examples:
- `docs/TOOL-3-META-DESCRIPTION-CHECKER-ACTION-PLAN-V2.md`
- `docs/ADMIN-DASHBOARD-REDESIGN-ACTION-PLAN-V2.md`

### Executive Summary:
```
docs/[FEATURE-NAME]-SUMMARY-V2.md
```

Examples:
- `docs/TOOL-3-META-DESCRIPTION-CHECKER-SUMMARY-V2.md`
- `docs/ADMIN-DASHBOARD-REDESIGN-SUMMARY-V2.md`

---

## ⏱️ Time Benchmarks

| Section | Target Time | Notes |
|---------|-------------|-------|
| Section 1-2 | 10 mins | Requirements + Implementation |
| Section 3 | 15 mins | Gap Analysis + Closure Loop |
| Section 4 | 10 mins | Optimization Strategy |
| Section 5 | 15 mins | Risk Assessment |
| Section 6 | 10 mins | Deployment Process |
| Section 7 | 5 mins | Executive Summary |
| Final Review | 5 mins | Readiness Checklist |
| **Total** | **70-80 mins** | **v1.1 Workflow** |

**Efficiency Tips:**
- Run section checklists during drafting (not at the end)
- Use gap closure template (copy-paste)
- Reuse risk matrix format
- Keep executive summary concise (3 pages max)

---

## 🎯 Quality Gates (Traffic Light System)

Use this status system while creating action plans:

```
Section Status:
🟢 Complete & Verified - Checklist passed, can proceed
🟡 In Progress - Currently working on it
🔴 Blocked - Issue preventing completion
⚪ Not Started - Queued for later
```

Example:
```
1. Feature Requirements      [🟢 Complete] ✅ Verified
2. Technical Implementation   [🟢 Complete] ✅ Verified
3. Gap Analysis              [🟡 In Progress] ⏸️ Pending closure table
4. Optimization Strategy     [⚪ Not Started]
5. Risk Assessment           [⚪ Not Started]
6. Deployment Process        [⚪ Not Started]
7. Executive Summary         [⚪ Not Started]
```

---

## 💡 Quick Tips

### 🔍 Before Starting
- [ ] Read design_guidelines.md (if frontend)
- [ ] Check replit.md for project context
- [ ] Review similar existing features
- [ ] Verify required secrets available

### 📝 During Planning
- [ ] Run section checklists as you go (not at the end)
- [ ] Update Sections 1-2 when gaps are found (feedback loop)
- [ ] Quantify everything (time, bundle size, value, etc.)
- [ ] Use tables for clarity (risk matrix, gap closure, etc.)

### ✅ Before Presenting
- [ ] Run final readiness review (all 6 categories)
- [ ] Verify no TODO/TBD placeholder text
- [ ] Check all file paths are correct
- [ ] Ensure executive summary is non-technical

### 🚀 After Approval
- [ ] Implement in phases (use time estimates)
- [ ] Test as you build (don't batch at end)
- [ ] Update replit.md when complete

---

## 📊 Success Metrics

**Good Action Plan Indicators:**
- ✅ All 7 sections complete
- ✅ All section checklists passed
- ✅ Gap closure table shows 100% closed/documented
- ✅ Risk matrix complete with mitigation
- ✅ Executive summary under 3 pages
- ✅ Final readiness review passed
- ✅ Time estimate within 70-80 minutes

**Red Flags:**
- ❌ Sections missing or incomplete
- ❌ Placeholder text (TODO, TBD, etc.)
- ❌ Gaps identified but not fed back to Sections 1-2
- ❌ Risks without mitigation strategies
- ❌ Trade-offs without reasoning
- ❌ Technical jargon in executive summary
- ❌ Time estimate way over 80 minutes

---

## 🔄 Continuous Improvement

After each action plan, consider:
- What took longer than expected? (optimize next time)
- What sections were hardest? (improve template)
- What did final review catch? (prevent earlier)
- What feedback did user have? (incorporate)

**Log learnings in:** `docs/ACTION-PLANNING-LESSONS-LEARNED.md`

---

**Quick Reference v1.1** | Updated: Nov 9, 2025  
For full details, see: `docs/ACTION-PLAN-TEMPLATE.md`
