import { RegisterForm } from "@/components/forms/RegisterForm";
import { AuthPageShell } from "@/components/layout/AuthPageShell";

export default function RegisterPage() {
  return (
    <AuthPageShell
      title="Crear cuenta"
      description="Regístrate para acceder al backoffice de HealthCore."
    >
      <RegisterForm />
    </AuthPageShell>
  );
}
