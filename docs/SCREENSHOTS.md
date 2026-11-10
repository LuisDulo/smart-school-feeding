# Smart School Feeding Management System

Updated system screenshots  
School administrator, bursar, kitchen and super administrator dashboards and the meal report downloaded by a parent  
Screenshots taken on 10 November 2026  

The same screenshots are in the Word document [Smart_School_Feeding_Updated_Screenshots.docx](Smart_School_Feeding_Updated_Screenshots.docx).

## About this document

This document replaces the earlier screenshots in the final documentation. Every figure was taken from the running system, each one is numbered and labelled with the page it shows, and a short description explains what the page is for. Section 4 shows the meal report that a parent downloads from the mobile app.

The system was populated with demonstration data: three schools, 50 students at Strathmore Primary School, and meal and payment activity up to 10 November 2026. Anomaly flags marked DEMO, or with a payment reference starting with SIMULATED, were created by the demonstration generator so that the anomaly detectors can be shown working. They are not real transactions.

### What is new in this version

- Menu Management shows clear messages and confirmations when items and meal combinations are added or removed.
- Serve Meals allows a student to be served up to two meals a day, and shows how many meals the student has had today.
- Anomaly Flags has a new Meal Serving tab for unusual meals and repeated refusals, next to the existing Top-ups tab.
- Model Comparison moved to the super administrator dashboard. It now also compares two anomaly-detection models and shows the meal-serving detector.
- Demand Forecast uses the best-performing forecasting model automatically, instead of the user choosing one.
- The super administrator page for network summaries is now called Multischool Reports.
- Parents can download their child's meal report as a PDF or CSV file from the mobile app.

## 1. School administrator dashboard (Strathmore Primary School)

The school administrator has access to every page below. Screenshots were taken while signed in as the administrator of Strathmore Primary School.

The landing page for school staff. The cards show meals served today, money collected today, students with a low balance and anomaly flags waiting for review. The bar chart shows meals collected over the last seven days, and the panel on the right shows the predicted number of meals and cost for the coming days.

![Figure 1: Dashboard](screenshots/01-dashboard.jpg)

*Figure 1: Dashboard*

Every enrolled student with their current meal balance, the date it was last updated and a status (Active, Low or Inactive), so staff can see who needs a top-up. The list can be searched by name or filtered to low or zero balances. Only the top of the list is shown.

![Figure 2: Student Balances](screenshots/02-student-balances.jpg)

*Figure 2: Student Balances*

The school administrator sets the food items and their prices. Kitchen staff choose from these items when they serve a meal, and the meal cost is the sum of the items chosen. A message now explains what is missing when the name or price is blank, and a confirmation appears after an item is added or removed.

![Figure 3: Menu Management - Menu Items](screenshots/03-menu-management-menu-items.jpg)

*Figure 3: Menu Management - Menu Items*

Menu items can be grouped into a named combination such as Lunch Special (Beans, Rice and Sukuma Wiki). Kitchen staff can search for the combination instead of picking each item, and its price always follows the prices of the items inside it. The right-hand panel lists the combinations that exist. The form now shows a clear message when a name or items are missing.

![Figure 4: Menu Management - Meal Combinations](screenshots/04-menu-management-meal-combinations.jpg)

*Figure 4: Menu Management - Meal Combinations*

The daily log of meals served for a chosen date: the student, the items collected, the amount deducted, the time served, the kitchen staff member who served the meal and the student's balance afterwards. The header shows meals served, students enrolled and the attendance rate. Only the top of the log is shown.

![Figure 5: Meal Distribution](screenshots/05-meal-distribution.jpg)

*Figure 5: Meal Distribution*

Creates student accounts (name, email, password and a starting balance) and lists the school's students with their balance, linked guardians and a QR Card button for printing the card used at the serving counter. Only the top of the page is shown.

![Figure 6: Account Management - Students](screenshots/06-account-management-students.jpg)

*Figure 6: Account Management - Students*

Creates parent accounts and links them to one or more students in the same step. The list shows each parent with the children they are linked to. Only the top of the page is shown.

![Figure 7: Account Management - Parents](screenshots/07-account-management-parents.jpg)

*Figure 7: Account Management - Parents*

Links an existing parent to an existing student, so the parent can see that child's balance, top up and download reports. A student can have more than one guardian and a parent can have more than one child.

![Figure 8: Account Management - Link Parent to Student](screenshots/08-account-management-link-parent-to-student.jpg)

*Figure 8: Account Management - Link Parent to Student*

Requests from parents to let their child eat on credit up to an agreed amount. Each request shows the parent, the student, the amount and the reason, and the administrator can approve or reject it. Approving raises the student's credit limit but does not add money to the balance.

![Figure 9: Credit Requests](screenshots/09-credit-requests.jpg)

*Figure 9: Credit Requests*

Issues that parents raise from the mobile app, with the category, the parent, the student and the current status. Staff update an issue to In Progress or Resolved. The tabs filter by status.

![Figure 10: Support Issues](screenshots/10-support-issues.jpg)

*Figure 10: Support Issues*

Predicted meal demand for the next five days or the next month, with the estimated cost. Users no longer choose a model: the system automatically uses the best-performing forecasting model from the model comparison and states which one it is at the top of the page.

![Figure 11: Demand Forecast](screenshots/11-demand-forecast.jpg)

*Figure 11: Demand Forecast*

Uses the balance-risk classifier (a Random Forest) to predict which students are likely to run out of balance within seven days, so parents can be reminded to top up before it happens. The cards summarise the number of students at risk and the total checked.

![Figure 12: Balance Risk](screenshots/12-balance-risk.jpg)

*Figure 12: Balance Risk*

Unusual M-Pesa top-ups found by the Isolation Forest model. Each flag shows its severity (High, Medium or Low), the student, the amount, the anomaly score, the time and the M-Pesa reference. The administrator reviews a flag and marks it legitimate or confirmed irregular, with optional notes. Flags whose reference starts with SIMULATED were created by the demonstration generator.

![Figure 13: Anomaly Flags - Top-ups (part 1 of 2)](screenshots/13-anomaly-flags-top-ups-part-1-of-2.jpg)

*Figure 13: Anomaly Flags - Top-ups (part 1 of 2)*

![Figure 13 (continued): Anomaly Flags - Top-ups (part 2 of 2)](screenshots/13-anomaly-flags-top-ups-part-2-of-2.jpg)

*Figure 13 (continued): Anomaly Flags - Top-ups (part 2 of 2)*

New in this version. Unusual meal serving is flagged here: meals recorded outside serving hours or on a non-school day, a meal costing far more than the student's usual, statistical outliers found by the model, repeated refusals to serve a student past the daily limit, and a staff member who is refused repeatedly. Every flag lists the reason in plain language. Flags marked DEMO were created by the demonstration generator.

![Figure 14: Anomaly Flags - Meal Serving (part 1 of 2)](screenshots/14-anomaly-flags-meal-serving-part-1-of-2.jpg)

*Figure 14: Anomaly Flags - Meal Serving (part 1 of 2)*

![Figure 14 (continued): Anomaly Flags - Meal Serving (part 2 of 2)](screenshots/14-anomaly-flags-meal-serving-part-2-of-2.jpg)

*Figure 14 (continued): Anomaly Flags - Meal Serving (part 2 of 2)*

A summary of the last 90 days (students, money collected, transactions, meals served, average meals per day, anomaly flags and low-balance students) with three CSV downloads: payment collection, meal distribution and anomaly detection.

![Figure 15: Reports](screenshots/15-reports.jpg)

*Figure 15: Reports*

Lets a school administrator raise a report or question directly with the platform team (Webmasters Kenya) and follow its progress. Each report shows its category, status and any reply from the platform team.

![Figure 16: Platform Support](screenshots/16-platform-support.jpg)

*Figure 16: Platform Support*

## 2. Bursar and kitchen staff views

Other school roles see a smaller set of pages. The kitchen role is the one that records meals at the serving counter.

The bursar sees the same dashboard, but the sidebar only offers the pages a bursar needs: balances, meal distribution, credit requests, support issues, forecast, balance risk, anomaly flags and reports. Menu management, account management and platform support are not available to this role.

![Figure 17: Dashboard (bursar view)](screenshots/17-dashboard-bursar-view.jpg)

*Figure 17: Dashboard (bursar view)*

Kitchen staff see the same summary figures, but their sidebar is limited to Serve Meals, Meal Distribution and Demand Forecast.

![Figure 18: Dashboard (kitchen view)](screenshots/18-dashboard-kitchen-view.jpg)

*Figure 18: Dashboard (kitchen view)*

Kitchen staff search for a student by name (or scan the QR card) and see the student's balance and daily meal count. A student can now be served up to two meals a day. The row shows Served 1 of 2 today with a Serve Another button, and once the limit is reached the button is disabled and reads Limit reached.

![Figure 19: Serve Meals - student search with daily meal count](screenshots/19-serve-meals-student-search-with-daily-meal-count.jpg)

*Figure 19: Serve Meals - student search with daily meal count*

After pressing Serve, the staff member picks a ready-made combination or ticks individual food items. The total is calculated as items are chosen, and Confirm and Record deducts it from the student's balance.

![Figure 20: Serve Meals - choosing a meal or combination](screenshots/20-serve-meals-choosing-a-meal-or-combination.jpg)

*Figure 20: Serve Meals - choosing a meal or combination*

## 3. Super administrator dashboard

The super administrator belongs to the platform operator and can see and manage every school.

The first page of the super administrator, who runs the platform across all schools. It shows network totals (schools, students, meals served and money collected today), a 14-day chart of meals per school, recent activity and a performance table for each school.

![Figure 21: Network Overview](screenshots/21-network-overview.jpg)

*Figure 21: Network Overview*

Every school in the network as a card, with students, staff, meals served today, anomaly flags, the balance pool and the average balance per student. View School Dashboard opens that school's own dashboard.

![Figure 22: Schools Management](screenshots/22-schools-management.jpg)

*Figure 22: Schools Management*

Registers a new school together with its first administrator account in one step.

![Figure 23: Schools Management - Register New School](screenshots/23-schools-management-register-new-school.jpg)

*Figure 23: Schools Management - Register New School*

The drill-down for one school: the same figures its administrator sees, including a seven-day meal chart, recent flags and the students with the lowest balances.

![Figure 24: School drill-down dashboard (part 1 of 2)](screenshots/24-school-drill-down-dashboard-part-1-of-2.jpg)

*Figure 24: School drill-down dashboard (part 1 of 2)*

![Figure 24 (continued): School drill-down dashboard (part 2 of 2)](screenshots/24-school-drill-down-dashboard-part-2-of-2.jpg)

*Figure 24 (continued): School drill-down dashboard (part 2 of 2)*

Comparisons across schools: weekly collections per school, the distribution of student balances, and how accurate the demand forecast has been for each school.

![Figure 25: Network Analytics](screenshots/25-network-analytics.jpg)

*Figure 25: Network Analytics*

Moved here from the school dashboard. It compares the forecasting models (Linear Regression, Random Forest and XGBoost), the anomaly-detection models (Isolation Forest and Local Outlier Factor) and the balance-risk classifier. It also shows the new meal-serving anomaly detector, evaluated on held-out meals with injected anomalies.

![Figure 26: Model Comparison (part 1 of 2)](screenshots/26-model-comparison-part-1-of-2.jpg)

*Figure 26: Model Comparison (part 1 of 2)*

![Figure 26 (continued): Model Comparison (part 2 of 2)](screenshots/26-model-comparison-part-2-of-2.jpg)

*Figure 26 (continued): Model Comparison (part 2 of 2)*

Every student across all schools, with their school and balance. Only the top of the list is shown.

![Figure 27: All Students](screenshots/27-all-students.jpg)

*Figure 27: All Students*

Admins, bursars and kitchen staff across the network, which can be filtered by school.

![Figure 28: Staff Management](screenshots/28-staff-management.jpg)

*Figure 28: Staff Management*

Creates a staff account for any school by choosing the school, the role, the name, the email and a password.

![Figure 29: Staff Management - New Staff Account](screenshots/29-staff-management-new-staff-account.jpg)

*Figure 29: Staff Management - New Staff Account*

Anomaly flags from all schools in one queue, which can be filtered by school, severity and review status.

![Figure 30: Anomaly Flags (all schools)](screenshots/30-anomaly-flags-all-schools.jpg)

*Figure 30: Anomaly Flags (all schools)*

Reports that school administrators have sent to the platform team. The super administrator updates each one to In Progress or Resolved and can reply.

![Figure 31: School Reports](screenshots/31-school-reports.jpg)

*Figure 31: School Reports*

Network-wide summary of every school (students, money collected, meals served and anomaly flags) with CSV downloads of all payments and all meal distribution across the network. This page was called Network Reports in the previous version.

![Figure 32: Multischool Reports](screenshots/32-multischool-reports.jpg)

*Figure 32: Multischool Reports*

## 4. Meal report downloaded by a parent

A parent opens the Monthly Report screen of the mobile app and chooses the PDF or CSV button to download the report for a child. The PDF below is the file that was downloaded. It shows the child's name and school, the reporting period, the date it was generated and the current balance. A monthly summary lists the meals, the amount spent, the amount topped up, the number of top-ups and the average spend per day. After that comes every meal served, with the date, the items, the amount and the staff member who served it. This example is for Nancy Odhiambo from 1 June to 6 November 2026: 74 meals, KES 3,555.00 spent and KES 1,501.00 topped up. Meals from the earlier demonstration data have no itemised food, so their Items column shows "Meal".

![Figure 33: Meal report PDF, page 1: summary and first meals](screenshots/33-meal-report-pdf-page-1-summary-and-first-meals.jpg)

*Figure 33: Meal report PDF, page 1: summary and first meals*

![Figure 34: Meal report PDF, page 2: meals served (continued)](screenshots/34-meal-report-pdf-page-2-meals-served-continued.jpg)

*Figure 34: Meal report PDF, page 2: meals served (continued)*

![Figure 35: Meal report PDF, page 3: meals served (continued)](screenshots/35-meal-report-pdf-page-3-meals-served-continued.jpg)

*Figure 35: Meal report PDF, page 3: meals served (continued)*
