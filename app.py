import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, flash
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
DB_URL = os.getenv("DATABASE_URL")
EMBED_URL = os.getenv("LOOKER_EMBED_URL")

def db():
    return psycopg2.connect(DB_URL, sslmode="require",
                            cursor_factory=psycopg2.extras.RealDictCursor)

def ejecutar(sql, params=(), fetch=False):
    with db() as con, con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() if fetch else None

@app.context_processor
def contador():
    try:
        total = ejecutar("SELECT COUNT(*) AS n FROM paciente", fetch=True)[0]["n"]
    except Exception:
        total = 0
    return dict(total=total)

@app.route("/")
def dashboard():
    try:
        k = ejecutar(
            "SELECT "
            "(SELECT COUNT(*) FROM paciente) AS pacientes, "
            "(SELECT COUNT(*) FROM cita) AS citas, "
            "(SELECT COUNT(*) FROM doctor WHERE estado) AS doctores, "
            "(SELECT COALESCE(SUM(honorarios),0) FROM cita) AS honorarios",
            fetch=True)[0]
    except Exception:
        k = dict(pacientes=0, citas=0, doctores=0, honorarios=0)
    k["honorarios_mil"] = int(k["honorarios"] / 1000)
    return render_template("dashboard.html", embed=EMBED_URL, k=k)

@app.route("/nuevo")
def nuevo():
    return render_template("nuevo.html")

@app.route("/pacientes")
def pacientes():
    q = request.args.get("q", "").strip()
    if q:
        id_q = int(q) if q.isdigit() else -1
        lista = ejecutar(
            "SELECT * FROM paciente WHERE id = %s OR nombre ILIKE %s "
            "ORDER BY id DESC LIMIT 100",
            (id_q, f"%{q}%"), fetch=True)
    else:
        lista = ejecutar(
            "SELECT * FROM paciente ORDER BY id DESC LIMIT 100", fetch=True)
    return render_template("pacientes.html", pacientes=lista, q=q)

@app.route("/crear", methods=["POST"])
def crear():
    f = request.form
    ejecutar(
        "INSERT INTO paciente (nombre, direccion, genero, edad, telefono) "
        "VALUES (%s,%s,%s,%s,%s)",
        (f["nombre"], f["direccion"], f["genero"], int(f["edad"]), f["telefono"]))
    flash("Paciente guardado correctamente.")
    return redirect("/pacientes")

@app.route("/editar/<int:id>", methods=["POST"])
def editar(id):
    ejecutar("UPDATE paciente SET nombre=%s WHERE id=%s",
             (request.form["nombre"], id))
    flash("Paciente actualizado.")
    return redirect("/pacientes")

@app.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    ejecutar("DELETE FROM paciente WHERE id=%s", (id,))
    flash("Paciente eliminado.")
    return redirect("/pacientes")

if __name__ == "__main__":
    app.run(debug=True)