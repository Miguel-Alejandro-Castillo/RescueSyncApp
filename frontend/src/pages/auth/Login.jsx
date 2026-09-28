import { useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { login } from "../../services/authService";
import { useSession } from "../../auth/AuthContext";
import Brand from "../../components/layout/Brand";
import styles from "./Login.module.css";
export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const session = useSession();
  const from = location.state?.from;
  const destination = typeof from === "string" && from.startsWith("/") && !from.startsWith("//") && from !== "/login" ? from : "/dashboard";
  const [pending, setPending] = useState(false);
  const [visible, setVisible] = useState(false);
  const [errors, setErrors] = useState({});
  const usernameRef = useRef(null);
  const passwordRef = useRef(null);
  async function handleSubmit(event) {
    event.preventDefault();
    if (pending) return;
    const username = usernameRef.current.value.trim();
    const nextErrors = {};
    if (!username) nextErrors.username = "Ingresá tu usuario.";
    if (!passwordRef.current.value.trim())
      nextErrors.password = "Ingresá tu contraseña.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      (nextErrors.username ? usernameRef : passwordRef).current.focus();
      return;
    }
    setPending(true);
    try {
      await login(username, passwordRef.current.value);
      navigate(destination, { replace: true });
    } catch (error) {
      setErrors({ submit: error.message });
    } finally {
      setPending(false);
    }
  }
  if (session) return <Navigate to={destination} replace />;
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Brand light showIcon={false} />
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
              <label className="form-label" htmlFor="username">
                Usuario
              </label>
              <input
                ref={usernameRef}
                className="form-control"
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                placeholder="Tu usuario"
                required
                aria-invalid={Boolean(errors.username)}
                aria-describedby={errors.username ? "username-error" : undefined}
                onChange={() =>
                  setErrors((current) => ({ ...current, username: undefined }))
                }
              />
              {errors.username && (
                <p className="field-error" id="username-error" role="alert">
                  {errors.username}
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
            {errors.submit && <p className="field-error" role="alert">{errors.submit}</p>}
            <button className="btn btn-primary w-100" type="submit" disabled={pending}>
              {pending ? "Ingresando…" : "Acceder"}
            </button>
          </form>

        </div>

      </section>
    </main>
  );
}
