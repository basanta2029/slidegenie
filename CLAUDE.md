## SlideGenie Project Overview

SlideGenie is an AI-powered academic presentation generator focused on helping researchers and professors create professional presentations from their papers in minutes.

### Current Implementation Status
- ✅ Full authentication system (email/OAuth)
- ✅ AI-powered generation (Claude, OpenAI)
- ✅ Document processing (PDF, DOCX, LaTeX)
- ✅ Rich presentation editor
- ✅ Export to multiple formats (PPTX, PDF, LaTeX)
- ✅ Academic template library
- ⚠️ Payment system (UI ready, not integrated)
- ⚠️ Real-time collaboration (infrastructure only)
- ❌ Analytics dashboard (placeholder)

### Key Project Guidelines

1. **MVP Focus**: We are building for individual researchers, NOT enterprises
   - No team management features
   - No enterprise SSO or complex permissions
   - No multi-language support (English only)
   - No API access for external integration

2. **Target Users**: 
   - Primary: PhD students creating conference presentations
   - Secondary: Professors creating lectures and talks
   - NOT: Large institutions or research teams

3. **Core Features Only**:
   - Upload paper → Generate presentation → Edit → Export
   - Simple sharing via links
   - Two pricing tiers: Free (3/month) and Pro ($9/month)

4. **Technical Constraints**:
   - Keep infrastructure simple and cost-effective
   - Optimize for 100 concurrent users, not thousands
   - 95% uptime target, not 99.9%

5. **UI/UX Principles**:
   - Academic-first design language
   - Clear visual hierarchy
   - Trust through transparency (beta status, realistic claims)
   - Mobile-responsive but desktop-first

### Development Rules

1. **Feature Development**:
   - Always check PRD_MVP.md before adding features
   - If it's not in the MVP PRD, don't build it
   - Focus on polishing existing features over adding new ones

2. **Code Quality**:
   - TypeScript for all frontend code
   - Proper error handling and user feedback
   - Comprehensive type definitions
   - Follow existing patterns in codebase

3. **Testing**:
   - Test with real academic content
   - Verify exports work correctly
   - Check responsive design
   - Validate all form inputs

4. **Performance**:
   - Optimize for <45 second generation time
   - Keep bundle size reasonable
   - Lazy load heavy components
   - Cache where appropriate

## Workflow Preferences
- Run all the agents for different tasks at the same time
- When pushing code to GitHub, proceed without asking for permission
- Focus on completing existing features before starting new ones
- Always update PRD_MVP.md when scope changes