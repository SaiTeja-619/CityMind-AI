import React from "react";
import { AIAnalysisData } from "@/types/complaint";
import { PriorityBadge } from "@/components/complaints/priority-badge";
import {
  Sparkles,
  BrainCircuit,
  Building2,
  Layers,
  AlertTriangle,
  Flame,
  CheckCircle2,
  Info,
} from "lucide-react";

interface AIAnalysisCardProps {
  data?: AIAnalysisData | null;
  className?: string;
  isProcessing?: boolean;
}

export function AIAnalysisCard({
  data,
  className = "",
  isProcessing = false,
}: AIAnalysisCardProps) {
  const predictedCategory = data?.category_prediction?.category || data?.predicted_category;
  const confidence = data?.category_prediction?.confidence ?? data?.category_confidence ?? 0;
  const isLowConfidence = data?.is_low_confidence ?? (confidence > 0 && confidence < 0.45);

  const deptName = data?.recommended_department?.name || data?.recommended_department_name;
  const deptCode = data?.recommended_department?.code || data?.recommended_department_code;

  const priority = data?.priority_prediction?.priority || data?.predicted_priority;
  const urgencyScore = data?.priority_prediction?.urgency_score ?? data?.urgency_score;

  const modelVersion = data?.model_version || "tfidf-logreg-v1";
  const hasAnalysis = !!predictedCategory;

  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-blue-100 text-blue-700">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              AI Complaint Analysis
            </h3>
            <p className="text-[11px] text-slate-500">
              Automated classification, department routing & priority estimation
            </p>
          </div>
        </div>

        <span className="text-[10px] font-mono font-semibold tracking-wider px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-600">
          {hasAnalysis ? modelVersion : "Triage Engine"}
        </span>
      </div>

      <div className="p-5">
        {!hasAnalysis ? (
          /* Unavailable / Pending State (No fake data) */
          <div className="py-6 px-4 text-center">
            <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-2.5">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <h4 className="text-xs font-semibold text-slate-700 mb-1">
              AI analysis is pending or currently unavailable.
            </h4>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
              Civic grievances are automatically evaluated by the CityMind ML classification engine upon submission.
            </p>
          </div>
        ) : (
          /* Real ML Pipeline Output */
          <div className="space-y-4">
            {/* Low-confidence alert banner if applicable */}
            {isLowConfidence && (
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold block">Low Model Confidence — Verification Advised</span>
                  <span className="text-[11px] text-amber-700">
                    The model probability estimate is below threshold. Municipal administrator verification is recommended.
                  </span>
                </div>
              </div>
            )}

            {/* Core Decision-Support Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {/* 1. Category Classification */}
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span className="flex items-center gap-1.5 font-medium">
                    <Layers className="w-3.5 h-3.5 text-blue-600" />
                    Predicted Category
                  </span>
                  <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded ${
                    isLowConfidence
                      ? "bg-amber-100 text-amber-800"
                      : "bg-emerald-100 text-emerald-800"
                  }`}>
                    {(confidence * 100).toFixed(1)}% prob
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1.5">
                  {predictedCategory}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  ML NLP Classifier
                </div>
              </div>

              {/* 2. Department Recommendation */}
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span className="flex items-center gap-1.5 font-medium">
                    <Building2 className="w-3.5 h-3.5 text-blue-600" />
                    Recommended Department
                  </span>
                  {deptCode && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">
                      {deptCode}
                    </span>
                  )}
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1.5">
                  {deptName || "—"}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  AI-assisted jurisdiction routing
                </div>
              </div>

              {/* 3. Priority Recommendation */}
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span className="flex items-center gap-1.5 font-medium">
                    <Flame className="w-3.5 h-3.5 text-amber-600" />
                    Recommended Priority
                  </span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  {priority ? (
                    <PriorityBadge priority={priority} />
                  ) : (
                    <span className="text-xs text-slate-600">—</span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Severity & hazard assessment
                </div>
              </div>

              {/* 4. Urgency Score */}
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span className="flex items-center gap-1.5 font-medium">
                    <Info className="w-3.5 h-3.5 text-blue-600" />
                    Calculated Urgency
                  </span>
                  {urgencyScore !== undefined && (
                    <span className="text-[11px] font-mono font-semibold text-slate-700">
                      {(urgencyScore * 100).toFixed(0)} / 100
                    </span>
                  )}
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mt-2">
                  <div
                    className={`h-full transition-all duration-300 ${
                      (urgencyScore || 0) >= 0.75
                        ? "bg-rose-500"
                        : (urgencyScore || 0) >= 0.55
                        ? "bg-amber-500"
                        : (urgencyScore || 0) >= 0.35
                        ? "bg-blue-500"
                        : "bg-slate-400"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, (urgencyScore || 0) * 100))}%` }}
                  />
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Decision-support risk index
                </div>
              </div>
            </div>

            {/* Model Provenance Footer */}
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                Real Model Evaluation
              </span>
              <span>TF-IDF + Multinomial Logistic Regression</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
