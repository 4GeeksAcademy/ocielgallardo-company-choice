const form = document.getElementById("application-form");
const statusEl = document.getElementById("status");

const fields = {
  fullName: {
    input: document.getElementById("fullName"),
    error: document.getElementById("fullName-error"),
    validate(value) {
      if (!value.trim()) return "El nombre es obligatorio.";
      if (value.trim().length < 3) return "El nombre debe tener al menos 3 caracteres.";
      return "";
    }
  },
  email: {
    input: document.getElementById("email"),
    error: document.getElementById("email-error"),
    validate(value) {
      if (!value.trim()) return "El correo es obligatorio.";
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) return "Ingresa un correo válido.";
      return "";
    }
  },
  phone: {
    input: document.getElementById("phone"),
    error: document.getElementById("phone-error"),
    validate(value) {
      if (!value.trim()) return "El teléfono es obligatorio.";
      const digitsOnly = value.replace(/\D/g, "");
      if (digitsOnly.length !== 10) return "El teléfono debe tener 10 dígitos.";
      return "";
    }
  }
};

function clearStatus() {
  statusEl.textContent = "";
  statusEl.className = "";
}

function setFieldError(fieldKey, message) {
  const field = fields[fieldKey];
  field.error.textContent = message;
}

function validateField(fieldKey) {
  const field = fields[fieldKey];
  const message = field.validate(field.input.value);
  setFieldError(fieldKey, message);
  return !message;
}

function validateForm() {
  let isValid = true;

  for (const key of Object.keys(fields)) {
    const fieldValid = validateField(key);
    if (!fieldValid) isValid = false;
  }

  return isValid;
}

for (const key of Object.keys(fields)) {
  fields[key].input.addEventListener("input", () => {
    validateField(key);
    clearStatus();
  });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  if (!validateForm()) {
    statusEl.textContent = "Hay errores en el formulario.";
    statusEl.className = "fail";
    return;
  }

  statusEl.textContent = "Formulario válido. Listo para enviar.";
  statusEl.className = "ok";
});
