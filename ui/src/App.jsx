import { useState } from "react";
import {
  ShieldCheck,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Download,
  RefreshCw,
  Eye,
  FileCheck2,
  CircleAlert,
  ClipboardCheck,
  XCircle,
  Activity,
  Search
} from "lucide-react";
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import "./App.css";

const initialCase = {
  caseId: "PP-1001",
  invoice: "INV-2026-041",
  buyer: "ABC Manufacturing Ltd.",
  amount: 85000
};

const evidenceItems = [
  {
    name: "Invoice",
    reference: "E-001",
    source: "Demo invoice record",
    status: "Available in demo",
    kind: "verified",
    description: "Invoice information is available for human review."
  },
  {
    name: "Purchase Order",
    reference: "E-002",
    source: "Demo purchase order record",
    status: "Available in demo",
    kind: "verified",
    description: "Purchase order information is available for human review."
  },
  {
    name: "Delivery Proof",
    reference: "E-003",
    source: "Not provided",
    status: "Missing",
    kind: "missing",
    description: "Delivery evidence has not been provided."
  }
];

function App() {
  const [role, setRole] = useState("Owner");
  const [filter, setFilter] = useState("All");
  const [reminderStatus, setReminderStatus] = useState("Pending review");
  const [recoveryStatus, setRecoveryStatus] = useState("Ready");

  const [events, setEvents] = useState([
    {
      time: new Date().toLocaleTimeString(),
      actor: "ProofPay AI Demo",
      action: "Demo case loaded",
      result: "Sample data only"
    }
  ]);

  function addEvent(action, result) {
    setEvents(function (previous) {
      return [
        {
          time: new Date().toLocaleTimeString(),
          actor: role,
          action: action,
          result: result
        },
        ...previous
      ];
    });
  }

  const filteredEvidence = evidenceItems.filter(function (item) {
    if (filter === "All") return true;
    if (filter === "Verified") return item.kind === "verified";
    if (filter === "Missing") return item.kind === "missing";
    if (filter === "Mismatched") return item.kind === "mismatched";
    return true;
  });

  function exportPDF() {
    try {
      const doc = new jsPDF();
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();

      doc.setFont("helvetica", "bold");
      doc.setFontSize(20);
      doc.text("ProofPay AI", 14, 18);

      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      doc.text("Case Review Package - DEMO DATA", 14, 26);

      doc.setFontSize(14);
      doc.text("Case Summary", 14, 38);

      autoTable(doc, {
        startY: 44,
        head: [["Field", "Value"]],
        body: [
          ["Case ID", initialCase.caseId],
          ["Invoice", initialCase.invoice],
          ["Buyer", initialCase.buyer],
          ["Invoice Amount", "INR 85,000"],
          ["Case Status", "Needs review"],
          ["Data Status", "Demonstration data"]
        ],
        theme: "grid",
        headStyles: { fillColor: [36, 95, 197] },
        styles: { fontSize: 9, cellPadding: 3 }
      });

      let y = doc.lastAutoTable.finalY + 12;

      if (y > pageHeight - 45) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(14);
      doc.text("Evidence Index", 14, y);

      autoTable(doc, {
        startY: y + 5,
        head: [["Evidence", "Reference", "Status", "Source"]],
        body: evidenceItems.map(function (item) {
          return [
            item.name,
            item.reference,
            item.status,
            item.source
          ];
        }),
        theme: "grid",
        headStyles: { fillColor: [36, 95, 197] },
        styles: { fontSize: 8, cellPadding: 3 }
      });

      y = doc.lastAutoTable.finalY + 12;

      if (y > pageHeight - 45) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(14);
      doc.text("Decision and Next Action", 14, y);

      doc.setFontSize(10);

      const decisionText =
        "The estimate is blocked because delivery proof is missing and the applicable rule has not been verified. Obtain the missing evidence and verify the relevant rule before producing a confirmed estimate.";

      const decisionLines = doc.splitTextToSize(
        decisionText,
        pageWidth - 28
      );

      doc.text(decisionLines, 14, y + 8);

      y += 12 + decisionLines.length * 5;

      if (y > pageHeight - 45) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(14);
      doc.text("Reminder Draft", 14, y);

      doc.setFontSize(10);

      const reminderLines = doc.splitTextToSize(
        "Please provide the outstanding delivery proof so the case can be reviewed further.",
        pageWidth - 28
      );

      doc.text(reminderLines, 14, y + 8);

      y += 12 + reminderLines.length * 5;

      if (y > pageHeight - 45) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(14);
      doc.text("Audit Trail", 14, y);

      autoTable(doc, {
        startY: y + 5,
        head: [["Time", "Actor", "Action", "Result"]],
        body: events.map(function (event) {
          return [
            event.time,
            event.actor,
            event.action,
            event.result
          ];
        }),
        theme: "grid",
        headStyles: { fillColor: [36, 95, 197] },
        styles: { fontSize: 8, cellPadding: 2 }
      });

      const pageCount = doc.internal.getNumberOfPages();

      for (let page = 1; page <= pageCount; page += 1) {
        doc.setPage(page);
        doc.setFontSize(7);

        doc.text(
          "Draft for human review. Not legal advice. Nothing has been sent or filed.",
          14,
          pageHeight - 8
        );

        doc.text(
          "Page " + page + " of " + pageCount,
          pageWidth - 35,
          pageHeight - 8
        );
      }

      doc.save(initialCase.caseId + "-review-package.pdf");

      addEvent(
        "Case review package exported",
        "PDF download requested - demo data"
      );
    } catch (error) {
      console.error("PDF export failed:", error);

      window.alert(
        "PDF export failed. Press F12, open Console, and check the error."
      );
    }
  }

  function simulateFailure() {
    setRecoveryStatus("Recovery required");
    addEvent(
      "Failure scenario simulated",
      "Demo only - no real agent failure occurred"
    );
  }

  function resumeReview() {
    setRecoveryStatus("Demo resumed");
    addEvent(
      "Demo review resumed",
      "UI state restored; real agent recovery is not connected"
    );
  }

  function approveDraft() {
    setReminderStatus("Approved - Not Sent");
    addEvent("Reminder draft approved", "Approved - Not Sent");
  }

  function rejectDraft() {
    setReminderStatus("Rejected");
    addEvent("Reminder draft rejected", "Rejected - Not Sent");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={25} />
          </div>
          <div>
            <h2>ProofPay AI</h2>
            <span>Trust &amp; Evidence</span>
          </div>
        </div>

        <div className="side-label">WORKSPACE</div>

        <div className="nav-item active">
          <Activity size={18} />
          <span>Case Overview</span>
        </div>

        <div className="nav-item">
          <FileCheck2 size={18} />
          <span>Evidence Review</span>
        </div>

        <div className="nav-item">
          <ClipboardCheck size={18} />
          <span>Audit &amp; Approval</span>
        </div>

        <div className="sidebar-bottom">
          <ShieldCheck size={18} />
          <span>Human review required</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="page-heading">
            <div>
              <div className="eyebrow">PROOFPAY / CASE MANAGEMENT</div>
              <h1>Trust &amp; Evidence Review</h1>
              <p>Review case evidence, decisions, and audit history.</p>
            </div>
          </div>

          <label className="role-control">
            <span>View as</span>
            <select
              value={role}
              onChange={function (event) {
                setRole(event.target.value);
              }}
            >
              <option>Owner</option>
              <option>Accountant</option>
            </select>
          </label>
        </header>

        <div className="demo-banner">
          <AlertTriangle size={17} />
          <span>
            DEMONSTRATION MODE - Sample data only. Agent integration is pending.
          </span>
        </div>

        <section className="case-heading">
          <div>
            <div className="case-id">CASE ID: {initialCase.caseId}</div>
            <h2>{initialCase.buyer}</h2>
            <p>Invoice {initialCase.invoice} - Created for demonstration</p>
          </div>

          <span className="status-pill warning">
            <Clock3 size={15} />
            Needs Review
          </span>
        </section>

        <section className="summary-grid">
          <article className="summary-card">
            <div className="summary-top">
              <span>Evidence available</span>
              <div className="summary-icon blue">
                <FileText size={20} />
              </div>
            </div>
            <div className="summary-number">2</div>
            <div className="summary-caption">Invoice and purchase order</div>
          </article>

          <article className="summary-card">
            <div className="summary-top">
              <span>Missing evidence</span>
              <div className="summary-icon amber">
                <AlertTriangle size={20} />
              </div>
            </div>
            <div className="summary-number">1</div>
            <div className="summary-caption">Delivery proof required</div>
          </article>

          <article className="summary-card">
            <div className="summary-top">
              <span>Mismatches reported</span>
              <div className="summary-icon green">
                <CheckCircle2 size={20} />
              </div>
            </div>
            <div className="summary-number">0</div>
            <div className="summary-caption">Based on current demo data</div>
          </article>

          <article className="summary-card">
            <div className="summary-top">
              <span>Invoice amount</span>
              <div className="summary-icon purple">
                <ClipboardCheck size={20} />
              </div>
            </div>
            <div className="summary-number amount">₹85,000</div>
            <div className="summary-caption">Illustrative amount</div>
          </article>
        </section>

        <section className="content-grid">
          <article className="panel evidence-panel">
            <div className="panel-header">
              <div>
                <h3>Evidence Review</h3>
                <p>Inspect the evidence reported for this case.</p>
              </div>
              <div className="panel-heading-icon">
                <Search size={18} />
              </div>
            </div>

            <div className="filter-row">
              {["All", "Verified", "Missing", "Mismatched"].map(function (item) {
                return (
                  <button
                    key={item}
                    className={
                      "filter-button " +
                      (filter === item ? "selected" : "")
                    }
                    onClick={function () {
                      setFilter(item);
                    }}
                  >
                    {item}
                  </button>
                );
              })}
            </div>

            <div className="evidence-list">
              {filteredEvidence.map(function (item) {
                return (
                  <div className="evidence-item" key={item.reference}>
                    <div className={"evidence-icon " + item.kind}>
                      {item.kind === "verified" ? (
                        <CheckCircle2 size={19} />
                      ) : item.kind === "missing" ? (
                        <CircleAlert size={19} />
                      ) : (
                        <XCircle size={19} />
                      )}
                    </div>

                    <div className="evidence-details">
                      <div className="evidence-title-row">
                        <h4>{item.name}</h4>
                        <span className={"evidence-status " + item.kind}>
                          {item.status}
                        </span>
                      </div>

                      <p>{item.description}</p>

                      <span className="evidence-source">
                        {item.reference} - {item.source}
                      </span>
                    </div>

                    <button
                      className="icon-button"
                      title="View evidence details"
                      onClick={function () {
                        window.alert(
                          item.name +
                            "\nSource: " +
                            item.source +
                            "\nStatus: " +
                            item.status +
                            "\n" +
                            item.description
                        );
                      }}
                    >
                      <Eye size={18} />
                    </button>
                  </div>
                );
              })}

              {filteredEvidence.length === 0 && (
                <div className="empty-state">
                  No items in this category are reported in the demo data.
                </div>
              )}
            </div>
          </article>

          <article className="panel decision-panel">
            <div className="panel-header">
              <div>
                <h3>Agent Decision</h3>
                <p>Decision transparency</p>
              </div>
              <div className="panel-heading-icon">
                <ShieldCheck size={19} />
              </div>
            </div>

            <div className="decision-status">
              <AlertTriangle size={19} />
              <div>
                <strong>Estimate blocked</strong>
                <span>Verification required</span>
              </div>
            </div>

            <h4>Why was the estimate blocked?</h4>
            <p className="decision-explanation">
              Delivery proof is missing, and the applicable rule has not been
              verified. No confirmed estimate is available in this demo.
            </p>

            <div className="decision-divider" />

            <h4>Recommended next action</h4>

            <div className="next-action">
              <CheckCircle2 size={18} />
              <span>
                Obtain the missing delivery evidence and verify the applicable
                rule before producing a confirmed estimate.
              </span>
            </div>

            <div className="source-note">
              <FileText size={17} />
              <div>
                <strong>Rule source</strong>
                <span>No verified rule source connected in this demo.</span>
              </div>
            </div>
          </article>
        </section>

        <section className="content-grid lower-grid">
          <article className="panel recovery-panel">
            <div className="panel-header">
              <div>
                <h3>Failure &amp; Recovery</h3>
                <p>Demonstration controls</p>
              </div>
              <RefreshCw size={19} className="muted-icon" />
            </div>

            <div className="recovery-state">
              <span
                className={
                  "recovery-dot " +
                  (recoveryStatus === "Ready" ? "ready" : "attention")
                }
              />

              <div>
                <strong>{recoveryStatus}</strong>
                <p>
                  UI demonstration only. Real agent checkpoint recovery is not
                  connected yet.
                </p>
              </div>
            </div>

            <div className="button-row">
              <button className="secondary-button" onClick={simulateFailure}>
                <AlertTriangle size={16} />
                Simulate Failure
              </button>

              <button className="primary-button" onClick={resumeReview}>
                <RefreshCw size={16} />
                Resume Demo
              </button>
            </div>
          </article>

          <article className="panel approval-panel">
            <div className="panel-header">
              <div>
                <h3>Human Review</h3>
                <p>Nothing is sent automatically</p>
              </div>
              <ClipboardCheck size={19} className="muted-icon" />
            </div>

            <div className="reminder-box">
              <div className="reminder-heading">
                <FileText size={17} />
                <strong>Reminder draft</strong>
              </div>

              <p>
                Please provide the outstanding delivery proof so the case can
                be reviewed further.
              </p>
            </div>

            <div className="review-status">
              Status: <strong>{reminderStatus}</strong>
            </div>

            <div className="button-row">
              <button className="primary-button" onClick={approveDraft}>
                <CheckCircle2 size={16} />
                Approve Draft
              </button>

              <button className="secondary-button" onClick={rejectDraft}>
                <XCircle size={16} />
                Reject
              </button>
            </div>

            <p className="safety-note">
              Approval records a demo decision only. No message is sent.
            </p>
          </article>
        </section>

        <section className="panel audit-panel">
          <div className="panel-header">
            <div>
              <h3>Audit Timeline</h3>
              <p>Recent events recorded by this dashboard session.</p>
            </div>
            <Activity size={19} className="muted-icon" />
          </div>

          <div className="audit-table-wrapper">
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Result</th>
                </tr>
              </thead>

              <tbody>
                {events.map(function (event, index) {
                  return (
                    <tr key={event.time + "-" + index}>
                      <td>{event.time}</td>
                      <td>{event.actor}</td>
                      <td>{event.action}</td>
                      <td>{event.result}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="export-banner">
          <div className="export-icon">
            <FileCheck2 size={24} />
          </div>

          <div className="export-copy">
            <h3>Export Case Review Package</h3>
            <p>
              Download a PDF containing the case summary, evidence index,
              decision, reminder draft, and current demo audit history.
            </p>
          </div>

          <button className="export-button" onClick={exportPDF}>
            <Download size={18} />
            Export PDF
          </button>
        </section>

        <footer className="app-footer">
          <ShieldCheck size={16} />
          <span>
            ProofPay AI - Draft for human review - Not legal advice - Nothing
            has been sent or filed
          </span>
        </footer>
      </main>
    </div>
  );
}

export default App;