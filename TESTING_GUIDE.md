# Quick Testing Guide
## 38 Premium Modules - Ready to Test

### Prerequisites
1. Start the application: `python3 app.py`
2. Login as superadmin or testuser@example.com
3. Company 3 (ViTracker) has all 38 modules enabled

---

## Module Access Testing

### Phase 1: Foundation & Quick Wins

#### 1. Export Data Module
- **URL:** http://localhost:5001/tenders/list (look for Export dropdown)
- **Test:** Click "Export CSV", "Export Excel", "Export PDF"
- **Expected:** Download files in respective formats

#### 2. Bulk Operations Module
- **URL:** http://localhost:5001/tenders/list (select checkboxes)
- **Test:** Click "Bulk Actions", select tenders, change status
- **Expected:** Multiple tenders updated at once

#### 3. Advanced Search Module
- **URL:** http://localhost:5001/search/advanced
- **Test:** Enter search criteria, save search, load saved search
- **Expected:** Filtered results, saved searches persist

#### 4. Analytics Module
- **URL:** http://localhost:5001/analytics/dashboard
- **Test:** View KPI cards and charts
- **Expected:** 4 KPI cards + 4 charts rendering

---

### Phase 2: Reporting & Analytics

#### 5. Advanced Reporting
- **URL:** http://localhost:5001/reports/
- **Test:** Generate "Tender Summary Report", export to Excel
- **Expected:** Report displays, Excel downloads

#### 6. Win/Loss Analytics
- **URL:** http://localhost:5001/win-loss/
- **Test:** View win rate dashboard and charts
- **Expected:** Win/loss stats + 3 charts displaying

---

### Phase 3: Document Management

#### 7. Document Management
- **URL:** http://localhost:5001/documents/
- **Test:** Upload document, download, search
- **Expected:** Files stored in uploads/documents/{company_id}/

#### 8. Template Library
- **URL:** http://localhost:5001/templates/
- **Test:** Create template, download template
- **Expected:** Templates stored and retrievable

---

### Phase 4: Collaboration & Communication

#### 9. Collaborative Workspace
- **URL:** http://localhost:5001/workspace/
- **Test:** Create workspace, add members, post discussion
- **Expected:** Workspace created, discussions visible

#### 10. CRM Module
- **URL:** http://localhost:5001/crm/
- **Test:** Add contact, create organization, log interaction
- **Expected:** CRM data persisted and displayed

---

### Phase 5: South African Compliance

#### 11. BBBEE Tracker
- **URL:** http://localhost:5001/bbbee/
- **Test:** Update BBBEE profile, view scorecard
- **Expected:** Scorecard calculates level (1-8)

#### 12. Compliance Q&A
- **URL:** http://localhost:5001/compliance/
- **Test:** Create checklist, answer compliance questions
- **Expected:** Compliance tracking and completion rates

---

### Phase 6: AI & Intelligence

#### 13. AI Tender Writer
- **URL:** http://localhost:5001/ai-writer/
- **Test:** Generate proposal, view AI document
- **Expected:** AI-generated content displayed

#### 14. Predictive Scoring
- **URL:** http://localhost:5001/predictive/
- **Test:** View tender predictions, analyze factors
- **Expected:** Win probability scores calculated

---

### Phase 7: Opportunity Management

#### 15. Tender Scraper
- **URL:** http://localhost:5001/scraper/
- **Test:** Add source, run scraper, import discovery
- **Expected:** Discovered tenders imported to system

#### 16. Resource Planner
- **URL:** http://localhost:5001/resources/
- **Test:** Allocate resource to tender, view capacity
- **Expected:** Capacity tracking and timeline display

---

### Phase 8: Integration & Advanced

#### 17. Email/Calendar Integration
- **URL:** http://localhost:5001/integrations/
- **Test:** Configure email, configure calendar
- **Expected:** Integration settings saved

#### 18. API Access
- **URL:** http://localhost:5001/api/v1/keys
- **Test:** Create API key, test endpoints
- **Expected:** API key generated, endpoints respond

---

## API Testing Commands

### Create API Key (via browser)
1. Login to http://localhost:5001
2. Enable "api_access" module for Company 3
3. Navigate to /api/v1/keys
4. Click "Create API Key"
5. Copy the generated key

### Test API Endpoints (via curl)
```bash
# Replace YOUR_API_KEY with actual key
API_KEY="YOUR_API_KEY"

# List tenders
curl -H "X-API-Key: $API_KEY" http://localhost:5001/api/v1/tenders

# Get tender by ID
curl -H "X-API-Key: $API_KEY" http://localhost:5001/api/v1/tenders/1

# Create tender
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"title":"API Test Tender","category":"IT","value":50000}' \
  http://localhost:5001/api/v1/tenders

# Get statistics
curl -H "X-API-Key: $API_KEY" http://localhost:5001/api/v1/stats
```

---

## Features Dropdown Verification

### Check Module Visibility
1. Login as testuser@example.com (Company 3)
2. Look at navigation menu
3. Find "Features" dropdown (should show badge "38")
4. Click dropdown - all 38 modules should be listed

### Module Categories
- **Premium Modules (19):** Advanced features
- **Feature Modules (19):** Enhanced capabilities
- **Core Modules:** Base system features

---

## Common Test Scenarios

### Scenario 1: Complete Tender Workflow with All Modules
1. **Scraper:** Discover new tender
2. **Import:** Import to system
3. **Predictive:** Check win probability score
4. **Resource Planner:** Allocate team members
5. **Workspace:** Create project workspace
6. **Compliance:** Complete compliance checklist
7. **BBBEE:** Verify BBBEE requirements
8. **AI Writer:** Generate proposal
9. **Documents:** Upload supporting documents
10. **Export:** Export tender data for review
11. **Analytics:** Track in dashboard

### Scenario 2: Reporting Workflow
1. **Advanced Search:** Find specific tenders
2. **Save Search:** Save criteria for reuse
3. **Analytics:** View KPIs and charts
4. **Reports:** Generate detailed report
5. **Export:** Download as Excel
6. **Win/Loss:** Analyze performance

### Scenario 3: Team Collaboration
1. **CRM:** Add client contact
2. **Workspace:** Create tender workspace
3. **Invite:** Add team members
4. **Discussion:** Post updates
5. **Resource Planner:** Check capacity
6. **Email Integration:** Sync communications

---

## Troubleshooting

### Module Not Visible
- Verify module is enabled in `company_modules` table
- Check `is_enabled = 1` for Company 3
- Verify user has company_id = 3

### Permission Denied
- Check user role has permission
- Verify `@module_required('module_name')` decorator
- Ensure `can_access_module()` returns True

### Database Errors
- Check `saved_searches` table exists
- Verify foreign key constraints
- Run: `SHOW TABLES LIKE 'saved_searches';`

### File Upload Issues
- Check directory permissions for `uploads/` folder
- Verify company subdirectories are created
- Ensure sufficient disk space

---

## Performance Testing

### Load Test Scenarios
1. **Bulk Operations:** Select 100 tenders, change status
2. **Export:** Export 1000 tenders to Excel
3. **Analytics:** Load dashboard with 1 year data
4. **Search:** Complex search with 5 filters
5. **API:** 100 concurrent API requests

### Expected Response Times
- Simple pages: < 200ms
- Complex analytics: < 1s
- Reports: < 2s
- Exports: < 5s (depends on data size)
- API endpoints: < 100ms

---

## Next Steps After Testing

1. **Bug Fixes:** Address any errors found
2. **UI Polish:** Improve template styling
3. **Integration:** Connect real AI/scraping services
4. **Documentation:** Create user guides
5. **Training:** Train users on new features
6. **Deployment:** Move to production

---

## Success Criteria

✅ All 38 modules accessible
✅ No permission errors for enabled modules
✅ All CRUD operations working
✅ File uploads/downloads successful
✅ Charts and visualizations rendering
✅ API authentication working
✅ Database operations committing
✅ Activity logging captured

**Happy Testing! 🚀**
