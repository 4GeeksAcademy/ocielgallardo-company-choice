const form = document.getElementById("application-form");
const statusElement = document.getElementById("form-status");

const invalidInputClasses = ["border-red-500", "ring-2", "ring-red-500/30", "bg-red-50"];
const validInputClasses = ["border-emerald-500", "ring-2", "ring-emerald-500/20", "bg-emerald-50"];

const validators = {
  fullName(value) {
    const trimmed = value.trim();
    if (!trimmed) return "El nombre completo es obligatorio.";
    if (trimmed.length < 3) return "El nombre debe tener al menos 3 caracteres.";
    return "";
  },
  dob(value) {
    if (!value) return "La fecha de nacimiento es obligatoria.";
    const birthDate = new Date(value);
    const now = new Date();
    const age = now.getFullYear() - birthDate.getFullYear();
    const monthDiff = now.getMonth() - birthDate.getMonth();
    const dayDiff = now.getDate() - birthDate.getDate();
    const adjustedAge = monthDiff < 0 || (monthDiff === 0 && dayDiff < 0) ? age - 1 : age;
    if (adjustedAge < 18) return "Debes ser mayor de 18 anos para registrarte.";
    return "";
  },
  email(value) {
    if (!value.trim()) return "El email es obligatorio.";
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(value.trim())) return "Ingresa un email valido.";
    return "";
  },
  phone(value) {
    if (!value.trim()) return "El telefono es obligatorio.";
    const digits = value.replace(/\D/g, "");
    if (digits.length < 10 || digits.length > 15) return "El telefono debe tener entre 10 y 15 digitos.";
    return "";
  },
  country(value) {
    const trimmed = value.trim();
    if (!trimmed) return "El pais es obligatorio.";
    if (trimmed.length < 2) return "Ingresa un pais valido.";
    return "";
  },
  address(value) {
    const trimmed = value.trim();
    if (!trimmed) return "La direccion es obligatoria.";
    if (trimmed.length < 10) return "La direccion debe tener al menos 10 caracteres.";
    return "";
  },
  consultationType(value) {
    if (!value) return "Selecciona un tipo de consulta.";
    return "";
  },
  preferredClinic(value) {
    if (!value) return "Selecciona una clinica preferida.";
    return "";
  },
  insuranceProvider(value) {
    const trimmed = value.trim();
    if (!trimmed) return "El seguro medico es obligatorio.";
    if (trimmed.length < 3) return "Ingresa un nombre de seguro valido.";
    return "";
  },
  medicalHistory(value) {
    const trimmed = value.trim();
    if (!trimmed) return "El historial medico basico es obligatorio.";
    if (trimmed.length < 15) return "El historial medico debe tener al menos 15 caracteres.";
    return "";
  },
  consent(value, element) {
    if (!element.checked) return "Debes aceptar el tratamiento de datos para continuar.";
    return "";
  }
};

function getErrorElement(fieldName) {
  return document.getElementById(`${fieldName}-error`);
}

function setFieldState(element, isValid) {
  element.classList.remove(...invalidInputClasses, ...validInputClasses);

  if (isValid) {
    element.classList.add(...validInputClasses);
  } else {
    element.classList.add(...invalidInputClasses);
  }
}

function validateField(fieldName) {
  const element = form.elements[fieldName];
  const validator = validators[fieldName];
  const errorElement = getErrorElement(fieldName);

  if (!element || !validator || !errorElement) {
    return true;
  }

  const value = element.type === "checkbox" ? element.checked : element.value;
  const errorMessage = validator(value, element);

  errorElement.textContent = errorMessage;
  element.setAttribute("aria-invalid", errorMessage ? "true" : "false");

  if (element.type !== "checkbox") {
    setFieldState(element, !errorMessage);
  }

  return !errorMessage;
}

function validateForm() {
  const fieldNames = Object.keys(validators);
  let firstInvalidField = null;
  let allValid = true;

  fieldNames.forEach((fieldName) => {
    const isValid = validateField(fieldName);
    if (!isValid) {
      allValid = false;
      if (!firstInvalidField) {
        firstInvalidField = form.elements[fieldName];
      }
    }
  });

  if (firstInvalidField) {
    firstInvalidField.focus();
  }

  return allValid;
}

function resetFeedback() {
  statusElement.textContent = "";
  statusElement.className = "min-h-6 text-sm font-medium";

  Object.keys(validators).forEach((fieldName) => {
    const element = form.elements[fieldName];
    const errorElement = getErrorElement(fieldName);

    if (errorElement) {
      errorElement.textContent = "";
    }

    if (element) {
      element.setAttribute("aria-invalid", "false");
      if (element.type !== "checkbox") {
        element.classList.remove(...invalidInputClasses, ...validInputClasses);
      }
    }
  });
}

Object.keys(validators).forEach((fieldName) => {
  const element = form.elements[fieldName];
  if (!element) return;

  const eventName = element.type === "checkbox" || element.tagName === "SELECT" ? "change" : "input";

  element.addEventListener(eventName, () => {
    validateField(fieldName);
    statusElement.textContent = "";
  });

  element.addEventListener("blur", () => {
    validateField(fieldName);
  });
});

form.addEventListener("submit", (event) => {
  event.preventDefault();

  if (!validateForm()) {
    statusElement.textContent = "Revisa los campos marcados en rojo antes de enviar.";
    statusElement.className = "min-h-6 text-sm font-medium text-red-700";
    return;
  }

  statusElement.textContent = "Registro enviado con exito. Un asesor de HealthCore te contactara pronto.";
  statusElement.className = "min-h-6 text-sm font-medium text-emerald-700";
  form.reset();

  Object.keys(validators).forEach((fieldName) => {
    const element = form.elements[fieldName];
    if (element && element.type !== "checkbox") {
      element.classList.remove(...invalidInputClasses, ...validInputClasses);
      element.setAttribute("aria-invalid", "false");
    }
  });
});

form.addEventListener("reset", () => {
  window.requestAnimationFrame(() => {
    resetFeedback();
  });
});
