"use client";

import { useSearchParams } from "next/navigation";
import { ResetPasswordForm } from "@/components/forms/ResetPasswordForm";

export function ResetPasswordTokenReader() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  return <ResetPasswordForm token={token} />;
}
