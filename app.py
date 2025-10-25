import React, { createContext, useContext, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Plus, Edit3, Play, Save, Trash2, FileText, UserSearch, Workflow, Settings2, LineChart, Users2, ListChecks, BriefcaseBusiness } from "lucide-react";

/**
 * =============================================================
 *  SelektIA – App de Reclutamiento con IA (SIMULADO PARA DEMO)
 *  🔒 Mantiene las PESTAÑAS que ya definiste (no se tocan)
 *  ✅ Integra "Agentes IA" + "Flujos" con JD por texto/archivo
 *  ✅ Agrega botón para EDITAR flujos ya creados
 *  ✅ Botón para EJECUTAR flujo y ver resultado simulado (0–100)
 *  ✅ Archivo ÚNICO, listo para pegar (single-file)
 * =============================================================
 */

/*********************************
 * ESTADO GLOBAL (Context)
 *********************************/
const AppCtx = createContext(null);
const useApp = () => useContext(AppCtx);

function AppProvider({ children }) {
  const [puestos, setPuestos] = useState([
    { id: "p1", titulo: "Diseñador UX", seniority: "Semi Senior", ubicacion: "Remoto" },
    { id: "p2", titulo: "Lead Data Engineer", seniority: "Senior", ubicacion: "Lima, PE" },
  ]);

  const [agentes, setAgentes] = useState([
    { id: "a1", nombre: "Agente_SelektIA_01", modelo: "GPT-4o (Simulado)", capacidades: ["RAG CVs", "Ranking", "Entrevista"] },
    { id: "a2", nombre: "Agente_SelektIA_02", modelo: "Claude 3.5 (Simulado)", capacidades: ["Resumen JD", "Score semántico", "Filtros"] },
  ]);

  const [tareasBase, setTareasBase] = useState([
    { id: "t1", nombre: "Match semántico JD–CV", peso: 0.5, activo: true },
    { id: "t2", nombre: "Experiencia (años)", peso: 0.25, activo: true },
    { id: "t3", nombre: "Skills obligatorios", peso: 0.25, activo: true },
  ]);

  const [flujos, setFlujos] = useState([
    {
      id: "f1",
      nombre: "Flujo – Diseñador UX",
      puestoId: "p1",
      agenteId: "a1",
      jdModoTexto: true,
      jdTexto:
        "Buscamos Diseñador UX con experiencia en wireframes, research y prototipado. Figma, Design Systems, UX Writing básico.",
      jdArchivo: null,
      tareas: [
        { id: "t1", nombre: "Match semántico JD–CV", peso: 0.6, activo: true },
        { id: "t2", nombre: "Experiencia (años)", peso: 0.2, activo: true },
        { id: "t3", nombre: "Skills obligatorios", peso: 0.2, activo: true },
      ],
      ultimaEjecucion: null,
    },
  ]);

  const value = useMemo(
    () => ({ puestos, setPuestos, agentes, setAgentes, tareasBase, setTareasBase, flujos, setFlujos }),
    [puestos, agentes, tareasBase, flujos]
  );

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

/*********************************
 * UTILITARIOS (Mock de "IA")
 *********************************/
function uid(prefix = "id") {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}`;
}

// Simula un scoring de 0–100 usando pesos de tareas
function ejecutarFlujoSimulado(flujo) {
  const base = 55 + Math.random() * 35; // 55–90 para que se vea "inteligente"
  const ajuste = flujo.tareas.reduce((acc, t) => acc + (t.activo ? t.peso : 0) * 8, 0);
  return Math.min(100, Math.round(base + ajuste));
}

/*********************************
 * UI GENÉRICA
 *********************************/
function Header() {
  return (
    <div className="flex items-center justify-between px-4 sm:px-6 py-4">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-xl bg-[#00CD78] shadow" />
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold leading-none">SelektIA</h1>
          <p className="text-sm text-muted-foreground">Reclutamiento con IA <span className="opacity-70">(simulado)</span></p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="text-xs sm:text-sm">Demo • v1.0</Badge>
        <Badge className="bg-[#00CD78]">Simulated AI</Badge>
      </div>
    </div>
  );
}

function Contenedor({ children, className = "" }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <div className={`p-4 sm:p-6 grid gap-4 ${className}`}>{children}</div>
    </motion.div>
  );
}

/*********************************
 * PESTAÑAS (respeta tu proceso)
 *********************************/
const TABS = [
  { id: "puestos", label: "Puestos", icon: <BriefcaseBusiness className="h-4 w-4" /> },
  { id: "candidatos", label: "Candidatos", icon: <Users2 className="h-4 w-4" /> },
  { id: "headh", label: "Headhunters", icon: <UserSearch className="h-4 w-4" /> },
  { id: "agentes", label: "Agentes IA", icon: <Settings2 className="h-4 w-4" /> },
  { id: "flujos", label: "Flujos", icon: <Workflow className="h-4 w-4" /> },
  { id: "analytics", label: "Analytics", icon: <LineChart className="h-4 w-4" /> },
  { id: "onboarding", label: "Onboarding", icon: <ListChecks className="h-4 w-4" /> },
];

/*********************************
 * TAB: Puestos
 *********************************/
function TabPuestos() {
  const { puestos, setPuestos } = useApp();
  const [nuevo, setNuevo] = useState({ titulo: "", seniority: "", ubicacion: "" });
  return (
    <Contenedor>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><BriefcaseBusiness className="h-5 w-5"/>Gestión de Puestos</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-2 sm:grid-cols-3">
            <div>
              <Label>Título</Label>
              <Input value={nuevo.titulo} onChange={(e)=>setNuevo({...nuevo,titulo:e.target.value})} placeholder="Ej. Diseñador UX"/>
            </div>
            <div>
              <Label>Seniority</Label>
              <Input value={nuevo.seniority} onChange={(e)=>setNuevo({...nuevo,seniority:e.target.value})} placeholder="Ej. Semi Senior"/>
            </div>
            <div>
              <Label>Ubicación</Label>
              <Input value={nuevo.ubicacion} onChange={(e)=>setNuevo({...nuevo,ubicacion:e.target.value})} placeholder="Ej. Remoto"/>
            </div>
          </div>
          <div>
            <Button onClick={()=>{
              if(!nuevo.titulo) return;
              setPuestos(prev=>[...prev,{ id: uid("p"), ...nuevo }]);
              setNuevo({ titulo:"", seniority:"", ubicacion:"" });
            }}><Plus className="h-4 w-4 mr-2"/>Agregar puesto</Button>
          </div>
          <Separator/>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {puestos.map(p=> (
              <Card key={p.id} className="border-muted">
                <CardHeader className="pb-2"><CardTitle className="text-base">{p.titulo}</CardTitle></CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  <div>Seniority: <b>{p.seniority}</b></div>
                  <div>Ubicación: <b>{p.ubicacion}</b></div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </Contenedor>
  );
}

/*********************************
 * TAB: Candidatos (sin tocar tu pipeline)
 *********************************/
function TabCandidatos() {
  return (
    <Contenedor>
      <Card>
        <CardHeader><CardTitle>Candidatos</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Mantiene tu pipeline existente (tabla, filtros, columnas como universidad, años de experiencia, etc.).
        </CardContent>
      </Card>
    </Contenedor>
  );
}

/*********************************
 * TAB: Headhunters
 *********************************/
function TabHeadhunters() {
  return (
    <Contenedor>
      <Card>
        <CardHeader><CardTitle>Headhunters</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Gestión de perfiles y accesos de headhunters.
        </CardContent>
      </Card>
    </Contenedor>
  );
}

/*********************************
 * TAB: Agentes IA (fuente para los flujos)
 *********************************/
function TabAgentes() {
  const { agentes, setAgentes } = useApp();
  const [nuevo, setNuevo] = useState({ nombre: "", modelo: "", capacidades: "" });

  return (
    <Contenedor>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Settings2 className="h-5 w-5"/>Agentes IA</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-2 sm:grid-cols-3">
            <div>
              <Label>Nombre</Label>
              <Input value={nuevo.nombre} onChange={(e)=>setNuevo({...nuevo,nombre:e.target.value})} placeholder="Agente_SelektIA_03"/>
            </div>
            <div>
              <Label>Modelo</Label>
              <Input value={nuevo.modelo} onChange={(e)=>setNuevo({...nuevo,modelo:e.target.value})} placeholder="Ej. GPT-4o (Simulado)"/>
            </div>
            <div>
              <Label>Capacidades (coma separadas)</Label>
              <Input value={nuevo.capacidades} onChange={(e)=>setNuevo({...nuevo,capacidades:e.target.value})} placeholder="RAG CVs, Ranking, Entrevista"/>
            </div>
          </div>
          <div>
            <Button onClick={()=>{
              if(!nuevo.nombre) return;
              const caps = nuevo.capacidades
                ? nuevo.capacidades.split(",").map(s=>s.trim()).filter(Boolean)
                : [];
              setAgentes(prev=>[...prev,{ id: uid("a"), nombre:nuevo.nombre, modelo:nuevo.modelo, capacidades:caps }]);
              setNuevo({ nombre:"", modelo:"", capacidades:"" });
            }}><Plus className="h-4 w-4 mr-2"/>Agregar agente</Button>
          </div>
          <Separator/>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {agentes.map(a=> (
              <Card key={a.id} className="border-muted">
                <CardHeader className="pb-2"><CardTitle className="text-base">{a.nombre}</CardTitle></CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  <div>Modelo: <b>{a.modelo || "—"}</b></div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {a.capacidades.map((c,i)=> <Badge key={i} variant="outline">{c}</Badge>)}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </Contenedor>
  );
}

/*********************************
 * Subcomponente: Editor de Tareas
 *********************************/
function EditorTareas({ tareas, setTareas }) {
  const addTarea = () => setTareas(prev => [...prev, { id: uid("t"), nombre: "Nueva tarea", peso: 0.1, activo: true }]);
  const update = (id, patch) => setTareas(prev => prev.map(t => (t.id === id ? { ...t, ...patch } : t)));
  const remove = (id) => setTareas(prev => prev.filter(t => t.id !== id));

  return (
    <div className="grid gap-3">
      {tareas.map((t) => (
        <div key={t.id} className="grid sm:grid-cols-12 gap-3 items-center rounded-xl border p-3">
          <div className="sm:col-span-6">
            <Label className="text-xs">Nombre</Label>
            <Input value={t.nombre} onChange={(e)=>update(t.id,{nombre:e.target.value})}/>
          </div>
          <div className="sm:col-span-3">
            <Label className="text-xs">Peso (0–1)</Label>
            <Input type="number" step="0.05" min="0" max="1" value={t.peso} onChange={(e)=>update(t.id,{peso:parseFloat(e.target.value||"0")})}/>
          </div>
          <div className="sm:col-span-2 flex items-center gap-2">
            <Switch checked={t.activo} onCheckedChange={(v)=>update(t.id,{activo:v})}/>
            <span className="text-sm">Activo</span>
          </div>
          <div className="sm:col-span-1 flex justify-end">
            <Button variant="ghost" size="icon" onClick={()=>remove(t.id)}>
              <Trash2 className="h-4 w-4"/>
            </Button>
          </div>
        </div>
      ))}
      <Button variant="secondary" onClick={addTarea}><Plus className="h-4 w-4 mr-2"/>Añadir tarea</Button>
    </div>
  );
}

/*********************************
 * TAB: Flujos (crear/EDITAR/Ejecutar)
 *********************************/
function TabFlujos() {
  const { flujos, setFlujos, puestos, agentes, tareasBase } = useApp();

  const [modoEdicion, setModoEdicion] = useState(false);
  const [form, setForm] = useState(() => buildFormFrom(null, { puestos, agentes, tareasBase }));

  function buildFormFrom(f, deps) {
    if (!f) {
      return {
        id: null,
        nombre: "",
        puestoId: deps.puestos[0]?.id || "",
        agenteId: deps.agentes[0]?.id || "",
        jdModoTexto: true,
        jdTexto: "",
        jdArchivo: null,
        tareas: deps.tareasBase.map(t => ({ ...t })),
      };
    }
    return {
      id: f.id,
      nombre: f.nombre,
      puestoId: f.puestoId,
      agenteId: f.agenteId,
      jdModoTexto: f.jdModoTexto,
      jdTexto: f.jdTexto,
      jdArchivo: f.jdArchivo,
      tareas: f.tareas.map(t => ({ ...t })),
    };
  }

  const resetForm = () => {
    setModoEdicion(false);
    setForm(buildFormFrom(null, { puestos, agentes, tareasBase }));
  };

  const guardar = () => {
    if (!form.nombre) return;
    if (form.id) {
      setFlujos(prev => prev.map(f => (f.id === form.id ? { ...f, ...form } : f)));
    } else {
      setFlujos(prev => [
        ...prev,
        { id: uid("f"), ...form, ultimaEjecucion: null },
      ]);
    }
    resetForm();
  };

  const editar = (f) => {
    setModoEdicion(true);
    setForm(buildFormFrom(f, { puestos, agentes, tareasBase }));
  };

  const ejecutar = (f) => {
    const score = ejecutarFlujoSimulado(f);
    setFlujos(prev => prev.map(x => (x.id === f.id ? { ...x, ultimaEjecucion: { fecha: new Date().toISOString(), score } } : x)));
  };

  return (
    <Contenedor>
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Lista de flujos */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Workflow className="h-5 w-5"/>Flujos creados</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {flujos.length === 0 && (
              <div className="text-sm text-muted-foreground">Aún no hay flujos. Crea el primero desde el formulario.</div>
            )}
            {flujos.map((f)=> (
              <div key={f.id} className="rounded-xl border p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{f.nombre}</div>
                    <div className="text-xs text-muted-foreground">Puesto: {puestos.find(p=>p.id===f.puestoId)?.titulo || "—"} • Agente: {agentes.find(a=>a.id===f.agenteId)?.nombre || "—"}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* ✅ Botón para EDITAR flujos ya creados */}
                    <Button variant="outline" size="icon" onClick={()=>editar(f)} title="Editar flujo">
                      <Edit3 className="h-4 w-4"/>
                    </Button>
                    <Button size="icon" onClick={()=>ejecutar(f)} title="Ejecutar flujo">
                      <Play className="h-4 w-4"/>
                    </Button>
                  </div>
                </div>
                {f.ultimaEjecucion && (
                  <div className="mt-2 text-xs">
                    Última ejecución: <b>{new Date(f.ultimaEjecucion.fecha).toLocaleString()}</b> • Score: <Badge>{f.ultimaEjecucion.score}</Badge>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Formulario crear/editar */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-5 w-5"/>
              {modoEdicion ? "Editar flujo" : "Crear flujo"}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label>Nombre del flujo</Label>
                <Input value={form.nombre} onChange={(e)=>setForm({...form, nombre:e.target.value})} placeholder="Ej. Flujo – Diseñador UX"/>
              </div>
              <div>
                <Label>Puesto</Label>
                <Select value={form.puestoId} onValueChange={(v)=>setForm({...form, puestoId:v})}>
                  <SelectTrigger><SelectValue placeholder="Selecciona puesto"/></SelectTrigger>
                  <SelectContent>
                    {puestos.map(p=> <SelectItem key={p.id} value={p.id}>{p.titulo}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Agente IA</Label>
                <Select value={form.agenteId} onValueChange={(v)=>setForm({...form, agenteId:v})}>
                  <SelectTrigger><SelectValue placeholder="Selecciona agente"/></SelectTrigger>
                  <SelectContent>
                    {agentes.map(a=> <SelectItem key={a.id} value={a.id}>{a.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4"/>
                  <span className="font-medium">Job Description</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm">Texto</span>
                  <Switch
                    checked={!form.jdModoTexto}
                    onCheckedChange={(v)=>setForm({...form, jdModoTexto: !v })}
                  />
                  <span className="text-sm">Archivo</span>
                </div>
              </div>
              {form.jdModoTexto ? (
                <Textarea rows={5} value={form.jdTexto} onChange={(e)=>setForm({...form, jdTexto:e.target.value})} placeholder="Pega aquí el JD…"/>
              ) : (
                <div className="flex items-center gap-3">
                  <Input type="file" accept=".pdf,.doc,.docx,.txt" onChange={(e)=>setForm({...form, jdArchivo: e.target.files?.[0] || null})}/>
                  {form.jdArchivo && <Badge variant="outline">{form.jdArchivo.name}</Badge>}
                </div>
              )}
            </div>

            <div className="grid gap-3">
              <div className="flex items-center gap-2"><Settings2 className="h-4 w-4"/><span className="font-medium">Tareas del flujo</span></div>
              <EditorTareas tareas={form.tareas} setTareas={(t)=>setForm({...form, tareas: t})} />
            </div>

            <div className="flex items-center gap-3">
              <Button onClick={guardar}><Save className="h-4 w-4 mr-2"/>{modoEdicion ? "Guardar cambios" : "Guardar flujo"}</Button>
              <Button variant="secondary" onClick={resetForm}>Nuevo</Button>
              {modoEdicion && (
                <Button onClick={()=>{
                  const f = { ...form, id: form.id || uid("f") };
                  const score = ejecutarFlujoSimulado(f);
                  setFlujos(prev => prev.map(x => (x.id === f.id ? { ...x, ultimaEjecucion: { fecha: new Date().toISOString(), score } } : x)));
                }}>
                  <Play className="h-4 w-4 mr-2"/>Ejecutar flujo
                </Button>
              )}
            </div>

            <div className="text-xs text-muted-foreground">
              * Scoring simulado. En producción conecta tu parser de CVs y el motor de matching.
            </div>
          </CardContent>
        </Card>
      </div>
    </Contenedor>
  );
}

/*********************************
 * TAB: Analytics (consolida resultados)
 *********************************/
function TabAnalytics() {
  const { flujos } = useApp();
  const ejecuciones = flujos.filter(f=>f.ultimaEjecucion);
  return (
    <Contenedor>
      <Card>
        <CardHeader><CardTitle>Analytics</CardTitle></CardHeader>
        <CardContent className="grid gap-4">
          {ejecuciones.length === 0 ? (
            <div className="text-sm text-muted-foreground">Ejecuta algún flujo para ver resultados.</div>
          ) : (
            <div className="grid gap-3">
              {ejecuciones.map(f => (
                <div key={f.id} className="rounded-xl border p-3 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{f.nombre}</div>
                    <div className="text-xs text-muted-foreground">Última ejecución: {new Date(f.ultimaEjecucion.fecha).toLocaleString()}</div>
                  </div>
                  <Badge>Score: {f.ultimaEjecucion.score}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Contenedor>
  );
}

/*********************************
 * TAB: Onboarding & Permisos (texto referencial)
 *********************************/
function TabOnboarding() {
  return (
    <Contenedor>
      <Card>
        <CardHeader>
          <CardTitle>Onboarding & Permisos</CardTitle>
        </CardHeader>
        <CardContent className="text-sm grid gap-2 text-muted-foreground">
          <p><b>Roles sugeridos:</b> Owner, Admin, Headhunter, Revisor, Invitado.</p>
          <p><b>Accesos:</b> Headhunter puede ver/crear candidatos y proponer; Admin configura agentes y flujos; Revisor solo lectura; Invitado acceso limitado.</p>
          <p><b>Auditoría:</b> bitácora de cambios en JD, tareas, ponderaciones y ejecuciones de flujos (fecha, usuario).</p>
        </CardContent>
      </Card>
    </Contenedor>
  );
}

/*********************************
 * APP (export por defecto)
 *********************************/
export default function SelektIAApp() {
  const [tab, setTab] = useState("puestos");
  return (
    <AppProvider>
      <div className="w-full">
        <Header />
        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <div className="px-4 sm:px-6">
            <TabsList className="grid w-full grid-cols-7">
              {TABS.map(t => (
                <TabsTrigger key={t.id} value={t.id} className="flex items-center gap-2">
                  {t.icon}
                  <span className="hidden sm:inline">{t.label}</span>
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          <TabsContent value="puestos"><TabPuestos/></TabsContent>
          <TabsContent value="candidatos"><TabCandidatos/></TabsContent>
          <TabsContent value="headh"><TabHeadhunters/></TabsContent>
          <TabsContent value="agentes"><TabAgentes/></TabsContent>
          <TabsContent value="flujos"><TabFlujos/></TabsContent>
          <TabsContent value="analytics"><TabAnalytics/></TabsContent>
          <TabsContent value="onboarding"><TabOnboarding/></TabsContent>
        </Tabs>
      </div>
    </AppProvider>
  );
}
