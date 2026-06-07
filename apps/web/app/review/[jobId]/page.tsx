"use client";

import { use } from "react";

import { ReviewClient } from "./client";

export default function ReviewPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  return <ReviewClient jobId={jobId} />;
}
