"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { PageHeader } from "@/components/layout/page-header";
import { StatusBadge } from "@/components/complaints/status-badge";
import { PriorityBadge } from "@/components/complaints/priority-badge";
import { AIAnalysisCard } from "@/components/complaints/ai-analysis-card";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { complaintsApi, ApiError } from "@/lib/api-client";
import { ComplaintAttachmentItem } from "@/components/complaints/complaint-attachment-item";
import {
  ComplaintDetailResponse,
  ComplaintStatus,
  ALLOWED_STATUS_TRANSITIONS,
  ComplaintPriority,
} from "@/types/complaint";
import { formatDate } from "@/lib/utils";
import {
  ArrowLeft,
  Calendar,
  Clock,
  FileText,
  FileImage,
  MapPin,
  ShieldCheck,
  Tag,
  History,
  Building,
  User,
  Paperclip,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  UserCheck,
  Phone,
  Mail,
  AlertTriangle,
  Send,
  Navigation,
} from "lucide-react";

export default function OfficerComplaintDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const complaintId = params?.id as string;

  // Data states
  const [complaint, setComplaint] = useState<ComplaintDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isForbidden, setIsForbidden] = useState<boolean>(false);

  // Status Update State
  const [isUpdatingStatus, setIsUpdatingStatus] = useState<boolean>(false);
  const [targetStatus, setTargetStatus] = useState<string>("");
  const [statusRemarks, setStatusRemarks] = useState<string>("");
  const [statusSubmitting, setStatusSubmitting] = useState<boolean>(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [statusSuccess, setStatusSuccess] = useState<string | null>(null);

  // Fetch Complaint Details
  const fetchComplaint = useCallback(async () => {
    if (!complaintId) return;
    setIsLoading(true);
    setError(null);
    setIsForbidden(false);
    try {
      const data = await complaintsApi.getById(complaintId);
      setComplaint(data);
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setIsForbidden(true);
          setError("Access denied: You are not authorized to view or manage this complaint. It is assigned to another officer or outside your jurisdiction.");
        } else if (err.status === 404) {
          setError("The requested complaint record was not found.");
        } else {
          setError(err.message);
        }
      } else {
        setError(err?.message || "Failed to load complaint details.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [complaintId]);

  useEffect(() => {
    fetchComplaint();
  }, [fetchComplaint]);

  // Handle Status Update Submission
  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetStatus || !complaint) return;

    setStatusSubmitting(true);
    setStatusError(null);
    setStatusSuccess(null);

    try {
      const updated = await complaintsApi.updateStatus(
        complaint.id,
        targetStatus,
        statusRemarks.trim() || undefined
      );
      setComplaint(updated);
      setStatusSuccess(`Status successfully updated to ${targetStatus}.`);
      setIsUpdatingStatus(false);
      setTargetStatus("");
      setStatusRemarks("");
    } catch (err: any) {
      setStatusError(err?.message || "Failed to update complaint status.");
    } finally {
      setStatusSubmitting(false);
    }
  };

  // Compute allowed transitions strictly from state machine
  const currentStatus = complaint?.status as ComplaintStatus;
  const allowedTransitions = currentStatus && ALLOWED_STATUS_TRANSITIONS[currentStatus]
    ? ALLOWED_STATUS_TRANSITIONS[currentStatus]
    : [];

  return (
    <DashboardLayout allowedRoles={["OFFICER", "ADMIN"]}>
      {/* Back Button */}
      <div className="mb-4">
        <Link
          href="/officer/complaints"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Assigned Complaints
        </Link>
      </div>

      {isLoading ? (
        <div className="py-12">
          <LoadingState message="Retrieving complaint details and history..." />
        </div>
      ) : isForbidden ? (
        <div className="py-8 bg-white border border-red-200 rounded-xl p-8 text-center max-w-xl mx-auto shadow-2xs">
          <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900 mb-1">Access Restricted</h3>
          <p className="text-xs text-slate-600 mb-6">
            {error || "This complaint is assigned to another municipal officer or outside your jurisdiction."}
          </p>
          <Link
            href="/officer/complaints"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Return to Your Work Queue
          </Link>
        </div>
      ) : error || !complaint ? (
        <div className="py-8">
          <ErrorState message={error || "Complaint details not available"} retry={fetchComplaint} />
        </div>
      ) : (
        <>
          {/* Header */}
          <PageHeader
            title={complaint.title}
            description={`Ticket ${complaint.ticket_number} • Filed on ${formatDate(complaint.created_at)}`}
            badge={
              <div className="flex items-center gap-2">
                <StatusBadge status={complaint.status} />
                {complaint.priority && (
                  <PriorityBadge priority={complaint.priority as ComplaintPriority} />
                )}
              </div>
            }
            actions={
              <button
                onClick={fetchComplaint}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            }
          />

          {/* Feedback Alerts */}
          {statusSuccess && (
            <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2 font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{statusSuccess}</span>
              </div>
              <button
                onClick={() => setStatusSuccess(null)}
                className="text-emerald-700 hover:text-emerald-900 font-bold ml-4"
              >
                &times;
              </button>
            </div>
          )}

          {statusError && (
            <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2 font-medium">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>{statusError}</span>
              </div>
              <button
                onClick={() => setStatusError(null)}
                className="text-rose-700 hover:text-rose-900 font-bold ml-4"
              >
                &times;
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
            {/* Left 2 Cols: Details, Media, and Timeline */}
            <div className="lg:col-span-2 space-y-6">
              {/* AI Decision Support & Triage Recommendation */}
              <AIAnalysisCard data={complaint.ai_analysis} />

              {/* Description & Location */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-5">
                <div>
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    Grievance Description
                  </h3>
                  <p className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">
                    {complaint.description}
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 block mb-1 font-medium">Category</span>
                    <span className="font-semibold text-slate-900">
                      {typeof complaint.category === "object" && complaint.category !== null
                        ? complaint.category.name
                        : String(complaint.category || "General")}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 block mb-1 font-medium">Location / Address</span>
                    <div className="flex items-start gap-1.5 text-slate-900 font-semibold">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
                      <span>{complaint.location || complaint.address || "Ward 4"}</span>
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-500 block mb-1 font-medium">GPS Coordinates</span>
                    <span className="font-mono text-slate-700 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 inline-flex items-center gap-1">
                      <Navigation className="w-3 h-3 text-slate-400" />
                      {complaint.latitude.toFixed(5)}, {complaint.longitude.toFixed(5)}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 block mb-1 font-medium">Last Modified</span>
                    <span className="text-slate-700">
                      {formatDate(complaint.updated_at || complaint.created_at)}
                    </span>
                  </div>
                </div>

                {(complaint.resolved_at || complaint.closed_at) && (
                  <div className="pt-3 border-t border-slate-100 grid grid-cols-2 gap-4 text-xs">
                    {complaint.resolved_at && (
                      <div>
                        <span className="text-slate-500 block mb-0.5">Resolved Timestamp</span>
                        <span className="font-semibold text-emerald-700">
                          {formatDate(complaint.resolved_at)}
                        </span>
                      </div>
                    )}
                    {complaint.closed_at && (
                      <div>
                        <span className="text-slate-500 block mb-0.5">Closed Timestamp</span>
                        <span className="font-semibold text-slate-700">
                          {formatDate(complaint.closed_at)}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Uploaded Media / Evidence Section */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileImage className="w-4 h-4 text-blue-700" />
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Attached Media & Photographic Evidence
                    </h3>
                  </div>
                  <span className="text-xs text-slate-500">
                    {complaint.attachments?.length || 0} file(s)
                  </span>
                </div>

                {complaint.attachments && complaint.attachments.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {complaint.attachments.map((att) => (
                      <ComplaintAttachmentItem
                        key={att.id}
                        complaintId={complaint.id}
                        attachment={att}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="py-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
                    No image evidence was attached to this complaint submission.
                  </div>
                )}
              </div>

              {/* Status Timeline / Audit Trail */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-5">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-blue-700" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Lifecycle Audit Timeline
                  </h3>
                </div>

                {complaint.status_history && complaint.status_history.length > 0 ? (
                  <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                    {complaint.status_history.map((h, idx) => (
                      <div key={h.id || idx} className="relative">
                        <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-blue-600 border-2 border-white ring-2 ring-blue-100" />
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap text-xs">
                            <span className="font-bold text-slate-900">
                              {h.old_status ? `${h.old_status} → ${h.new_status}` : h.new_status}
                            </span>
                            <span className="text-[11px] text-slate-400">
                              {formatDate(h.created_at)}
                            </span>
                          </div>
                          {h.remarks && (
                            <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                              &ldquo;{h.remarks}&rdquo;
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-4 text-center text-xs text-slate-400">
                    No status transition events recorded yet.
                  </div>
                )}
              </div>
            </div>

            {/* Right Col: Status Management, Citizen Info, Assignment */}
            <div className="space-y-6">
              {/* Status Update Card */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Status Management
                </h3>

                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                  <span className="text-slate-500 block mb-1">Current State</span>
                  <StatusBadge status={complaint.status} />
                </div>

                {allowedTransitions.length > 0 ? (
                  <form onSubmit={handleUpdateStatus} className="space-y-3.5">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Transition To:
                      </label>
                      <select
                        value={targetStatus}
                        onChange={(e) => setTargetStatus(e.target.value)}
                        required
                        className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-blue-500 bg-white text-slate-900 font-medium"
                      >
                        <option value="">Select next status transition...</option>
                        {allowedTransitions.map((nextStatus) => (
                          <option key={nextStatus} value={nextStatus}>
                            {nextStatus}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Operational Remarks / Notes:
                      </label>
                      <textarea
                        rows={3}
                        value={statusRemarks}
                        onChange={(e) => setStatusRemarks(e.target.value)}
                        placeholder="Detail field inspection findings, action taken, or completion remarks..."
                        className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-blue-500 text-slate-900 placeholder-slate-400"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={statusSubmitting || !targetStatus}
                      className="w-full py-2.5 px-4 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 shadow-2xs"
                    >
                      {statusSubmitting ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Updating Status...
                        </>
                      ) : (
                        <>
                          <Send className="w-3.5 h-3.5" />
                          Execute Transition
                        </>
                      )}
                    </button>
                  </form>
                ) : (
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center">
                    This grievance is in terminal status ({complaint.status}) and cannot be transitioned further.
                  </div>
                )}
              </div>

              {/* Citizen Information Card */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-3">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 uppercase tracking-wider">
                  <User className="w-3.5 h-3.5 text-slate-500" />
                  <span>Citizen Details</span>
                </div>

                <div className="space-y-2 text-xs text-slate-700">
                  <div>
                    <span className="text-slate-400 text-[11px] block">Full Name</span>
                    <span className="font-semibold text-slate-900">
                      {complaint.citizen?.full_name || "Confidential Citizen"}
                    </span>
                  </div>

                  {complaint.citizen?.email && (
                    <div>
                      <span className="text-slate-400 text-[11px] block">Email</span>
                      <div className="flex items-center gap-1.5 font-medium text-slate-800">
                        <Mail className="w-3 h-3 text-slate-400" />
                        <span>{complaint.citizen.email}</span>
                      </div>
                    </div>
                  )}

                  {complaint.citizen?.phone_number && (
                    <div>
                      <span className="text-slate-400 text-[11px] block">Phone Contact</span>
                      <div className="flex items-center gap-1.5 font-medium text-slate-800">
                        <Phone className="w-3 h-3 text-slate-400" />
                        <span>{complaint.citizen.phone_number}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Assignment Information Card */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-3">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 uppercase tracking-wider">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-700" />
                  <span>Assigned Officer Roster</span>
                </div>

                <div className="space-y-2 text-xs text-slate-700">
                  <div>
                    <span className="text-slate-400 text-[11px] block">Assigned Officer</span>
                    <span className="font-semibold text-slate-900">
                      {complaint.assigned_officer?.user?.full_name || "Assigned Officer"}
                    </span>
                  </div>

                  {complaint.assigned_officer?.badge_number && (
                    <div>
                      <span className="text-slate-400 text-[11px] block">Badge Number</span>
                      <span className="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        {complaint.assigned_officer.badge_number}
                      </span>
                    </div>
                  )}

                  {complaint.assigned_officer?.designation && (
                    <div>
                      <span className="text-slate-400 text-[11px] block">Designation</span>
                      <span className="font-medium text-slate-800">
                        {complaint.assigned_officer.designation}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
