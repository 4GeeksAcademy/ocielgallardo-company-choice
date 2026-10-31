import { RegisterForm } from "@/components/forms/RegisterForm";
import { AuthPageShell } from "@/components/layout/AuthPageShell";

export default function RegisterPage() {
  return (
    <AuthPageShell
      title="Create account"
      description="Sign up to access the HealthCore backoffice."
    >
      <RegisterForm />
    </AuthPageShell>
  );
}
