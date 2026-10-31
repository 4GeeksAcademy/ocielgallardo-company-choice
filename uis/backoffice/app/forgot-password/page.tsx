import { ForgotPasswordForm } from "@/components/forms/ForgotPasswordForm";
import { AuthPageShell } from "@/components/layout/AuthPageShell";

export default function ForgotPasswordPage() {
  return (
    <AuthPageShell
      title="Reset password"
      description="Enter your email and we will send you a link to create a new password."
    >
      <ForgotPasswordForm />
    </AuthPageShell>
  );
}
