import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Brand from "../../components/layout/Brand";
import styles from "./Login.module.css";
export default function Login() {
  const navigate = useNavigate();
  const [visible, setVisible] = useState(false);
  const [errors, setErrors] = useState({});
  const emailRef = useRef(null);
  const passwordRef = useRef(null);
  function handleSubmit(event) {
    event.preventDefault();
    const email = emailRef.current.value.trim();
    const nextErrors = {};
    if (!email) nextErrors.email = "Ingresá tu correo electrónico.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      nextErrors.email = "Ingresá un correo electrónico válido.";
    if (!passwordRef.current.value.trim())
      nextErrors.password = "Ingresá tu contraseña.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      (nextErrors.email ? emailRef : passwordRef).current.focus();
      return;
    }
    // Integrar aquí el servicio de autenticación. Solo navegación de demostración:
    // no se guardan credenciales ni se crea una sesión autenticada.
    navigate("/dashboard", { state: { loginPreview: true } });
  }
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Brand light showIcon={false} />
        <Link className={styles.back} to="/dashboard">
          ← Volver al inicio
        </Link>
      </header>
      <section className={styles.access} aria-labelledby="login-title">
        <div className={styles.formWrap}>
          <h1 id="login-title">Iniciar sesión</h1>
          <form
            className="form-stack"
            onSubmit={handleSubmit}
            noValidate
          >
            <div>
              <label className="form-label" htmlFor="email">
                Correo electrónico
              </label>
              <input
                ref={emailRef}
                className="form-control"
                id="email"
                name="email"
                type="email"
                autoComplete="username"
                placeholder="nombre@organizacion.org"
                required
                aria-invalid={Boolean(errors.email)}
                aria-describedby={errors.email ? "email-error" : undefined}
                onChange={() =>
                  setErrors((current) => ({ ...current, email: undefined }))
                }
              />
              {errors.email && (
                <p className="field-error" id="email-error" role="alert">
                  {errors.email}
                </p>
              )}
            </div>
            <div>
              <label className="form-label" htmlFor="password">
                Contraseña
              </label>
              <div className={styles.password}>
                <input
                  ref={passwordRef}
                  className="form-control"
                  id="password"
                  name="password"
                  type={visible ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Ingresá tu contraseña"
                  required
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={
                    errors.password ? "password-error" : undefined
                  }
                  onChange={() =>
                    setErrors((current) => ({
                      ...current,
                      password: undefined,
                    }))
                  }
                />
                <button
                  type="button"
                  onClick={() => setVisible(!visible)}
                  aria-label={
                    visible ? "Ocultar contraseña" : "Mostrar contraseña"
                  }
                  aria-pressed={visible}
                >
                  {visible ? "Ocultar" : "Mostrar"}
                </button>
              </div>
              {errors.password && (
                <p className="field-error" id="password-error" role="alert">
                  {errors.password}
                </p>
              )}
            </div>
            <button className="btn btn-primary w-100" type="submit">
              Acceder
            </button>
          </form>

        </div>

      </section>
    </main>
  );
}
