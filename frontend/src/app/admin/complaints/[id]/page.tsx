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
import { complaintsApi, adminApi, ApiError } from "@/lib/api-client";
import { ComplaintAttachmentItem } from "@/components/complaints/complaint-attachment-item";
import {
  ComplaintDetailResponse,
  AdminOfficer,
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
  Edit3,
  ExternalLink,
  Phone,
  Mail,
  Check,
  AlertTriangle,
} from "lucide-react";

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export default function AdminComplaintDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const complaintId = params?.id as string;

  // Data states
  const [complaint, setComplaint] = useState<ComplaintDetailResponse | null>(null);
  const [officers, setOfficers] = useState<AdminOfficer[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Assignment Modal / Form State
  const [isAssigning, setIsAssigning] = useState<boolean>(false);
  const [selectedOfficerId, setSelectedOfficerId] = useState<string>("");
  const [assignSubmitting, setAssignSubmitting] = useState<boolean>(false);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assignSuccess, setAssignSuccess] = useState<string | null>(null);

  // Status Update Form State
  const [isUpdatingStatus, setIsUpdatingStatus] = useState<boolean>(false);
  const [targetStatus, setTargetStatus] = useState<string>("");
  const [statusRemarks, setStatusRemarks] = useState<string>("");
  const [statusSubmitting, setStatusSubmitting] = useState<boolean>(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [statusSuccess, setStatusSuccess] = useState<string | null>(null);

  // Fetch Complaint & Officers
  const fetchData = useCallback(async () => {
    if (!complaintId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [compData, officersList] = await Promise.all([
        complaintsApi.getById(complaintId),
        adminApi.getOfficers().catch(() => []),
      ]);
      setComplaint(compData);
      setOfficers(officersList);
      if (compData.assigned_officer_id) {
        setSelectedOfficerId(compData.assigned_officer_id);
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError("The requested civic complaint record was not found.");
        } else if (err.status === 403) {
          setError("Access denied: You are not authorized to view this complaint.");
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
    fetchData();
  }, [fetchData]);

  // Handle Assign Officer
  const handleAssignOfficer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOfficerId || !complaint) return;

    setAssignSubmitting(true);
    setAssignError(null);
    setAssignSuccess(null);

    try {
      const updated = await complaintsApi.assignOfficer(complaint.id, selectedOfficerId);
      setComplaint(updated);
      setAssignSuccess("Officer successfully assigned.");
      setIsAssigning(false);
    } catch (err: any) {
      setAssignError(err?.message || "Failed to assign officer.");
    } finally {
      setAssignSubmitting(false);
    }
  };

  // Handle Status Update
  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetStatus || !complaint) return;

    setStatusSubmitting(true);
    setStatusError(null);
    setStatusSuccess(null);

    try {
      const updated = await complaintsApi.updateStatus(complaint.id, targetStatus, statusRemarks.trim() || undefined);
      setComplaint(updated);
      setStatusSuccess(`Status successfully transitioned to ${targetStatus}.`);
      setIsUpdatingStatus(false);
      setTargetStatus("");
      setStatusRemarks("");
    } catch (err: any) {
      setStatusError(err?.message || "Failed to update complaint status.");
    } finally {
      setStatusSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout allowedRoles={["ADMIN"]}>
        <div className="py-16">
          <LoadingState message="Retrieving grievance record, attachments, and audit lifecycle history..." />
        </div>
      </DashboardLayout>
    );
  }

  if (error || !complaint) {
    return (
      <DashboardLayout allowedRoles={["ADMIN"]}>
        <div className="mb-4">
          <Link
            href="/admin/complaints"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Complaint Ledger
          </Link>
        </div>
        <div className="py-8">
          <ErrorState
            title="Failed to Load Complaint Details"
            message={error || "Grievance not found"}
            retry={fetchData}
          />
        </div>
      </DashboardLayout>
    );
  }

  const categoryName =
    typeof complaint.category === "object" && complaint.category !== null
      ? complaint.category.name
      : typeof complaint.category === "string"
      ? complaint.category
      : "General";

  const currentStatus = complaint.status as ComplaintStatus;
  const allowedTransitions = ALLOWED_STATUS_TRANSITIONS[currentStatus] || [];

  return (
    <DashboardLayout allowedRoles={["ADMIN"]}>
      {/* Back Link */}
      <div className="mb-4">
        <Link
          href="/admin/complaints"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Complaint Ledger
        </Link>
      </div>

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
          <div className="flex items-center gap-2">
            <button
              onClick={fetchData}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
          </div>
        }
      />

      {/* Notification feedback banners */}
      {assignSuccess && (
        <div className="mb-4 p-3 rounded-lg border border-emerald-200 bg-emerald-50 text-xs text-emerald-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>{assignSuccess}</span>
          </div>
          <button onClick={() => setAssignSuccess(null)} className="text-emerald-600 hover:text-emerald-900 font-bold">
            &times;
          </button>
        </div>
      )}

      {statusSuccess && (
        <div className="mb-4 p-3 rounded-lg border border-emerald-200 bg-emerald-50 text-xs text-emerald-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>{statusSuccess}</span>
          </div>
          <button onClick={() => setStatusSuccess(null)} className="text-emerald-600 hover:text-emerald-900 font-bold">
            &times;
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Details (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI Decision Support & Triage Recommendation */}
          <AIAnalysisCard data={complaint.ai_analysis} />

          {/* Detailed Description */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-blue-600" />
              Detailed Grievance Description
            </h3>
            <p className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed bg-slate-50/70 p-4 rounded-lg border border-slate-100">
              {complaint.description}
            </p>
          </div>

          {/* Location & Geospatial Data */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-blue-600" />
              Geographic & Location Tagging
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-500 block">Reported Landmark / Address</span>
                <span className="font-medium text-slate-900 mt-0.5 block">
                  {complaint.address || complaint.location_text || complaint.location || "Not specified"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">GPS Coordinates (WGS-84)</span>
                <span className="font-mono text-slate-900 mt-0.5 block">
                  {complaint.latitude?.toFixed(6)}, {complaint.longitude?.toFixed(6)}
                </span>
              </div>
            </div>
          </div>

          {/* Citizen Contact Information */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <User className="w-4 h-4 text-blue-600" />
              Filer (Citizen) Information
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div>
                <span className="text-slate-500 block">Citizen Full Name</span>
                <span className="font-semibold text-slate-900 mt-0.5 block">
                  {complaint.citizen?.full_name || "Public Citizen"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Email Address</span>
                <span className="font-mono text-slate-700 mt-0.5 block">
                  {complaint.citizen?.email || "—"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Phone Number</span>
                <span className="text-slate-700 mt-0.5 block">
                  {complaint.citizen?.phone_number || "Not provided"}
                </span>
              </div>
            </div>
          </div>

          {/* Photographic Evidence & Attachments */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Paperclip className="w-4 h-4 text-blue-600" />
                Photographic & Media Evidence
              </h3>
              <span className="text-xs text-slate-500 font-medium">
                {complaint.attachments?.length || 0} file{complaint.attachments?.length !== 1 ? "s" : ""}
              </span>
            </div>

            {complaint.attachments && complaint.attachments.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {complaint.attachments.map((file) => (
                  <ComplaintAttachmentItem
                    key={file.id}
                    complaintId={complaint.id}
                    attachment={file}
                  />
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-lg">
                No photographic evidence was attached to this grievance report.
              </div>
            )}
          </div>

          {/* Audit Lifecycle Timeline / Status History */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <History className="w-4 h-4 text-blue-600" />
              Official Redressal Timeline & Status History
            </h3>

            {complaint.status_history && complaint.status_history.length > 0 ? (
              <div className="relative pl-6 space-y-5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                {complaint.status_history.map((log) => (
                  <div key={log.id} className="relative">
                    <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                    <div className="flex flex-wrap items-center justify-between gap-1 text-xs">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={log.new_status} />
                        {log.old_status && (
                          <span className="text-[11px] text-slate-400">
                            (from {log.old_status})
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-400">
                        {formatDate(log.created_at)}
                      </span>
                    </div>
                    {log.remarks && (
                      <p className="mt-1 text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                        {log.remarks}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-4 text-center text-slate-400 text-xs">
                No state transition history recorded yet.
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar: Administrative Controls & Metadata (1 col) */}
        <div className="space-y-6">
          {/* Administrative Actions Card */}
          <div className="bg-white rounded-xl border border-blue-200 p-5 shadow-sm space-y-4">
            <h4 className="font-bold text-xs uppercase tracking-wider text-blue-900 border-b border-blue-100 pb-2 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-blue-700" />
              Administrative Actions
            </h4>

            {/* Officer Assignment Action */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">Assigned Officer</span>
                <button
                  onClick={() => setIsAssigning(!isAssigning)}
                  className="text-xs font-medium text-blue-700 hover:text-blue-900 flex items-center gap-1"
                >
                  <UserCheck className="w-3.5 h-3.5" />
                  {complaint.assigned_officer ? "Reassign" : "Assign Officer"}
                </button>
              </div>

              {complaint.assigned_officer ? (
                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">
                      Badge: {complaint.assigned_officer.badge_number}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Dept #{complaint.assigned_officer.department_id}
                    </span>
                  </div>
                  {complaint.assigned_officer.user?.full_name && (
                    <div className="text-slate-700 font-medium">
                      {complaint.assigned_officer.user.full_name}
                    </div>
                  )}
                  {complaint.assigned_officer.designation && (
                    <div className="text-slate-500 text-[11px]">
                      {complaint.assigned_officer.designation}
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3 rounded-lg border border-dashed border-amber-300 bg-amber-50/50 text-xs text-amber-800">
                  No municipal officer currently assigned.
                </div>
              )}

              {/* Assignment Form */}
              {isAssigning && (
                <form onSubmit={handleAssignOfficer} className="p-3 rounded-lg border border-blue-200 bg-blue-50/40 space-y-3 text-xs">
                  <label className="block font-medium text-slate-700">Select Available Officer:</label>
                  <select
                    value={selectedOfficerId}
                    onChange={(e) => setSelectedOfficerId(e.target.value)}
                    required
                    className="w-full px-2.5 py-1.5 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
                  >
                    <option value="">-- Choose Officer --</option>
                    {officers.map((off) => (
                      <option key={off.id} value={off.id}>
                        {off.badge_number} - {off.full_name} ({off.department_name || `Dept #${off.department_id}`})
                      </option>
                    ))}
                  </select>

                  {assignError && (
                    <p className="text-[11px] text-rose-600 bg-rose-50 p-1.5 rounded border border-rose-200">
                      {assignError}
                    </p>
                  )}

                  <div className="flex items-center gap-2">
                    <button
                      type="submit"
                      disabled={assignSubmitting || !selectedOfficerId}
                      className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white rounded font-medium disabled:opacity-50 transition-colors"
                    >
                      {assignSubmitting ? "Assigning..." : "Confirm Assignment"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsAssigning(false)}
                      className="px-2.5 py-1.5 bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 rounded"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Status Update Action */}
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">Lifecycle Status</span>
                {allowedTransitions.length > 0 ? (
                  <button
                    onClick={() => setIsUpdatingStatus(!isUpdatingStatus)}
                    className="text-xs font-medium text-blue-700 hover:text-blue-900 flex items-center gap-1"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Transition Status
                  </button>
                ) : (
                  <span className="text-[11px] text-slate-400">Terminal State</span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <StatusBadge status={complaint.status} />
                <span className="text-[11px] text-slate-500">
                  {allowedTransitions.length > 0
                    ? `Can transition to: ${allowedTransitions.join(", ")}`
                    : "No further transitions permitted."}
                </span>
              </div>

              {/* Status Update Form */}
              {isUpdatingStatus && (
                <form onSubmit={handleUpdateStatus} className="p-3 rounded-lg border border-blue-200 bg-blue-50/40 space-y-3 text-xs">
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">Target Status:</label>
                    <select
                      value={targetStatus}
                      onChange={(e) => setTargetStatus(e.target.value)}
                      required
                      className="w-full px-2.5 py-1.5 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
                    >
                      <option value="">-- Choose New Status --</option>
                      {allowedTransitions.map((st) => (
                        <option key={st} value={st}>
                          {st}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-medium text-slate-700 mb-1">Remarks / Audit Note:</label>
                    <textarea
                      value={statusRemarks}
                      onChange={(e) => setStatusRemarks(e.target.value)}
                      rows={2}
                      placeholder="Add official remarks or reason..."
                      className="w-full px-2.5 py-1.5 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
                    />
                  </div>

                  {statusError && (
                    <p className="text-[11px] text-rose-600 bg-rose-50 p-1.5 rounded border border-rose-200">
                      {statusError}
                    </p>
                  )}

                  <div className="flex items-center gap-2">
                    <button
                      type="submit"
                      disabled={statusSubmitting || !targetStatus}
                      className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white rounded font-medium disabled:opacity-50 transition-colors"
                    >
                      {statusSubmitting ? "Updating..." : "Commit Status"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsUpdatingStatus(false)}
                      className="px-2.5 py-1.5 bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 rounded"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          {/* Ticket Metadata Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4 text-xs">
            <h4 className="font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-2">
              System Metadata
            </h4>

            <div>
              <span className="text-slate-500 block">Municipal Category</span>
              <span className="font-semibold text-slate-900 mt-0.5 block">
                {categoryName}
              </span>
              {complaint.category?.default_sla_hours && (
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Resolution Target SLA: {complaint.category.default_sla_hours} hours
                </span>
              )}
            </div>

            <div>
              <span className="text-slate-500 block">Municipal Database UUID</span>
              <span className="font-mono text-[11px] text-slate-600 break-all mt-0.5 block">
                {complaint.id}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Filer UUID</span>
              <span className="font-mono text-[11px] text-slate-600 break-all mt-0.5 block">
                {complaint.citizen_id}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Created Timestamp</span>
              <span className="text-slate-700 mt-0.5 block">
                {formatDate(complaint.created_at)}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Last Updated</span>
              <span className="text-slate-700 mt-0.5 block">
                {formatDate(complaint.updated_at)}
              </span>
            </div>

            {complaint.resolved_at && (
              <div>
                <span className="text-slate-500 block">Resolved At</span>
                <span className="text-emerald-700 font-medium mt-0.5 block">
                  {formatDate(complaint.resolved_at)}
                </span>
              </div>
            )}

            {complaint.closed_at && (
              <div>
                <span className="text-slate-500 block">Closed At</span>
                <span className="text-slate-700 font-medium mt-0.5 block">
                  {formatDate(complaint.closed_at)}
                </span>
              </div>
            )}
          </div>

          {/* Security Banner */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-500 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-blue-700 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-slate-700">Official Municipal Redressal</p>
              <p className="mt-0.5 text-slate-500">
                All status modifications and officer assignments are logged into the immutable database audit trail.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
