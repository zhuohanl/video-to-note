"use client";

import { use } from "react";

import { EditClient } from "./client";

export default function EditPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  return <EditClient jobId={jobId} />;
}
