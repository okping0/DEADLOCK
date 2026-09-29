import { useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem("token"));

  function handleLogout() {
    localStorage.removeItem("token");
    setAuthed(false);
  }

  return authed ? (
    <Dashboard onLogout={handleLogout} />
  ) : (
    <Login onLogin={() => setAuthed(true)} />
  );
}
