"use client";

import { use } from "react";

import { ExportClient } from "./client";

export default function ExportPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  return <ExportClient jobId={jobId} />;
}
