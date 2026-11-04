import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Layers, BarChart3, BellRing, Package } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { ErrorText, Field } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@stockpilot.dev");
  const [password, setPassword] = useState("admin1234");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <section className="login-hero">
        <div className="brand brand-lg">
          <div className="brand-mark">
            <Layers size={22} />
          </div>
          <span>StockPilot</span>
        </div>
        <h1>Inventory and orders, under control.</h1>
        <p>Track stock in real time, process orders end to end, and restock before you run out.</p>
        <ul>
          <li><Package size={18} /> Products, suppliers and purchase orders in one place</li>
          <li><BellRing size={18} /> Automatic low-stock alerts with one-click reordering</li>
          <li><BarChart3 size={18} /> Sales and inventory reports with CSV export</li>
        </ul>
      </section>
      <section className="login-panel">
        <form className="card login-card" onSubmit={submit}>
          <h2>Sign in</h2>
          <p className="muted">Use a demo account to explore.</p>
          <Field label="Email">
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </Field>
          <Field label="Password">
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <ErrorText error={error} />
          <button className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <div className="demo-accounts">
            <button type="button" className="link" onClick={() => { setEmail("admin@stockpilot.dev"); setPassword("admin1234"); }}>
              Admin demo
            </button>
            <span>·</span>
            <button type="button" className="link" onClick={() => { setEmail("staff@stockpilot.dev"); setPassword("staff1234"); }}>
              Staff demo
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
