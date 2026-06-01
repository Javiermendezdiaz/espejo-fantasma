#!/usr/bin/env python3
"""
Friction Detection Engine — FASE 2 Sprint 2
Validates couple responses and calculates compatibility/friction metrics.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ============ ENUMS ============

class Dimension(str, Enum):
    """5 dimensiones del diagnóstico de pareja"""
    CONCILIATION = "conciliation"      # Reconciliación / armonía
    FINANCES = "finances"              # Finanzas / dinero
    ROBUSTNESS = "robustness"          # Solidez / estabilidad
    PATRIMONY = "patrimony"            # Patrimonio / bienes
    PSYCHOLOGY = "psychology"          # Psicología / personalidad


# ============ DATA MODELS ============

@dataclass
class ValidationError:
    """Error de validación de respuestas"""
    field: str
    message: str
    value: any = None


@dataclass
class ValidationResult:
    """Resultado de validación de respuestas pareadas"""
    valid: bool
    errors: List[ValidationError]
    total_questions: int = 0
    invalid_questions: List[int] = None

    def __post_init__(self):
        if self.invalid_questions is None:
            self.invalid_questions = []


@dataclass
class FrictionQuestion:
    """Una pregunta con fricción alta (desacuerdo entre pareja)"""
    question_id: int                # q1...q500
    dimension: Dimension
    user_a_response: int            # 1-5
    user_b_response: int            # 1-5
    delta: int                      # abs(a - b), 0-4
    topic: str                      # Descripción breve de la pregunta


@dataclass
class DimensionFriction:
    """Fricción agregada por dimensión"""
    dimension: Dimension
    questions: List[int]            # q_ids en esta dimensión
    avg_delta: float                # 0-4 (promedio de deltas)
    max_delta: int                  # 0-4 (máximo delta individual)
    questions_with_max_delta: List[int]  # q_ids con delta máximo


@dataclass
class FrictionMap:
    """Mapa completo de fricción de una pareja"""
    couple_id: str
    dimension_frictions: Dict[str, DimensionFriction]  # {dimension: DimensionFriction}
    top_friction_questions: List[FrictionQuestion]     # Top 5-10 by delta
    compatibility_score: int                           # 0-100 (100=perfect agreement)
    total_questions: int = 500
    metadata: Dict = None                              # {user_a_avg_response, user_b_avg_response, etc}

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ============ VALIDATION ============

class ResponseValidator:
    """Valida estructura de respuestas pareadas"""

    MIN_QUESTIONS = 500
    MAX_QUESTIONS = 500
    MIN_RESPONSE = 1
    MAX_RESPONSE = 5

    @staticmethod
    def validate_answers(answers: Dict) -> ValidationResult:
        """
        Valida que las respuestas cumplan estructura exacta:
        - len(answers) == 500
        - keys: q1, q2, ..., q500
        - values: todos en [1, 5]

        Args:
            answers: Dict {q1: int, q2: int, ..., q500: int}

        Returns:
            ValidationResult with errors list
        """
        errors = []
        invalid_questions = []

        # Validar cantidad
        if not answers:
            errors.append(ValidationError(
                field="answers",
                message=f"Respuestas vacías. Se esperan {ResponseValidator.MAX_QUESTIONS} preguntas.",
                value=None
            ))
            return ValidationResult(valid=False, errors=errors, total_questions=0)

        if len(answers) != ResponseValidator.MAX_QUESTIONS:
            errors.append(ValidationError(
                field="length",
                message=f"Se esperan {ResponseValidator.MAX_QUESTIONS} preguntas, se recibieron {len(answers)}",
                value=len(answers)
            ))

        # Validar keys
        expected_keys = {f"q{i}": i for i in range(1, ResponseValidator.MAX_QUESTIONS + 1)}
        actual_keys = set(answers.keys())
        expected_key_set = set(expected_keys.keys())

        if actual_keys != expected_key_set:
            missing = expected_key_set - actual_keys
            extra = actual_keys - expected_key_set
            if missing:
                errors.append(ValidationError(
                    field="keys_missing",
                    message=f"Faltan preguntas: {sorted(missing)[:5]}... ({len(missing)} total)",
                    value=sorted(missing)
                ))
            if extra:
                errors.append(ValidationError(
                    field="keys_extra",
                    message=f"Preguntas extra: {sorted(extra)[:5]}... ({len(extra)} total)",
                    value=sorted(extra)
                ))

        # Validar valores
        for q_key, value in answers.items():
            try:
                val_int = int(value)
                if not (ResponseValidator.MIN_RESPONSE <= val_int <= ResponseValidator.MAX_RESPONSE):
                    q_num = int(q_key[1:])
                    invalid_questions.append(q_num)
                    errors.append(ValidationError(
                        field=q_key,
                        message=f"Valor fuera de rango [{ResponseValidator.MIN_RESPONSE}, {ResponseValidator.MAX_RESPONSE}]",
                        value=val_int
                    ))
            except (ValueError, TypeError) as e:
                q_num = int(q_key[1:]) if q_key.startswith('q') else 0
                invalid_questions.append(q_num)
                errors.append(ValidationError(
                    field=q_key,
                    message=f"Valor no es número: {value}",
                    value=value
                ))

        valid = len(errors) == 0
        return ValidationResult(
            valid=valid,
            errors=errors,
            total_questions=len(answers),
            invalid_questions=invalid_questions
        )

    @staticmethod
    def validate_open_answers_encrypted(open_answers: Optional[Dict]) -> ValidationResult:
        """
        Valida estructura de respuestas abiertas encriptadas.
        Esperado: {encrypted_op1: "ciphertext|nonce", encrypted_op2: "...", encrypted_op3: "..."}

        Args:
            open_answers: Dict con respuestas abiertas encriptadas

        Returns:
            ValidationResult
        """
        errors = []

        if open_answers is None:
            # Opcional, pero si viene debe tener estructura
            return ValidationResult(valid=True, errors=errors)

        expected_open = {"encrypted_op1", "encrypted_op2", "encrypted_op3"}
        actual_keys = set(open_answers.keys())

        if actual_keys != expected_open:
            missing = expected_open - actual_keys
            extra = actual_keys - expected_open
            if missing:
                errors.append(ValidationError(
                    field="open_answers_keys_missing",
                    message=f"Faltan: {missing}",
                    value=missing
                ))
            if extra:
                errors.append(ValidationError(
                    field="open_answers_keys_extra",
                    message=f"Extras: {extra}",
                    value=extra
                ))

        # Validar formato "ciphertext|nonce"
        for key, value in open_answers.items():
            if not isinstance(value, str) or "|" not in value:
                errors.append(ValidationError(
                    field=key,
                    message=f"Debe ser 'ciphertext|nonce' format",
                    value=value
                ))

        return ValidationResult(valid=len(errors) == 0, errors=errors)


# ============ FRICTION CALCULATION ============

class FrictionCalculator:
    """Calcula fricción conyugal a partir de respuestas de ambos usuarios"""

    # Mapeo de preguntas a dimensiones
    # En producción esto viene de data-schema-500.json
    QUESTION_DIMENSIONS = {}  # Será poblado en __init__ o cargado de schema

    def __init__(self, question_schema: Optional[Dict] = None):
        """
        Inicializa calculador con schema de preguntas.

        Args:
            question_schema: {q1: dimension, q2: dimension, ...}
                            O None para usar default (20 q por dimensión × 5)
        """
        if question_schema:
            self.question_dimensions = question_schema
        else:
            # Default: 20 preguntas × 5 dimensiones
            self.question_dimensions = self._build_default_schema()

    @staticmethod
    def _build_default_schema() -> Dict[str, Dimension]:
        """Construye schema por defecto: 100 q por dimensión"""
        schema = {}
        q_per_dim = 100
        for dim_idx, dim in enumerate(Dimension):
            start = dim_idx * q_per_dim + 1
            end = (dim_idx + 1) * q_per_dim + 1
            for q in range(start, end):
                schema[f"q{q}"] = dim.value
        return schema

    def calculate_friction(
        self,
        couple_id: str,
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int]
    ) -> FrictionMap:
        """
        Calcula fricción conyugal entre dos conjuntos de respuestas.

        Args:
            couple_id: ID de la pareja
            user_a_answers: {q1: 1-5, q2: 1-5, ..., q500: 1-5}
            user_b_answers: {q1: 1-5, q2: 1-5, ..., q500: 1-5}

        Returns:
            FrictionMap con métricas completas
        """
        # Calcular deltas
        deltas = {}  # {q_id: delta}
        for q_key in range(1, 501):
            q_str = f"q{q_key}"
            if q_str in user_a_answers and q_str in user_b_answers:
                a_val = user_a_answers[q_str]
                b_val = user_b_answers[q_str]
                delta = abs(int(a_val) - int(b_val))
                deltas[q_str] = delta

        # Agrupar por dimensión
        dimension_frictions = {}
        for dim in Dimension:
            dim_questions = [q_key for q_key, d in self.question_dimensions.items() if d == dim.value]
            dim_deltas = [deltas.get(q, 0) for q in dim_questions]

            if dim_deltas:
                avg_delta = sum(dim_deltas) / len(dim_deltas)
                max_delta = max(dim_deltas)
                max_delta_questions = [int(q[1:]) for q, d in zip(dim_questions, dim_deltas) if d == max_delta]
            else:
                avg_delta = 0
                max_delta = 0
                max_delta_questions = []

            dimension_frictions[dim.value] = DimensionFriction(
                dimension=dim,
                questions=[int(q[1:]) for q in dim_questions],
                avg_delta=round(avg_delta, 2),
                max_delta=max_delta,
                questions_with_max_delta=max_delta_questions
            )

        # Top friction questions (máx delta)
        top_friction = []
        for q_key, delta in sorted(deltas.items(), key=lambda x: x[1], reverse=True)[:10]:
            q_num = int(q_key[1:])
            dim_str = self.question_dimensions.get(q_key, "unknown")
            try:
                dim = Dimension(dim_str)
            except ValueError:
                dim = Dimension.CONCILIATION

            top_friction.append(FrictionQuestion(
                question_id=q_num,
                dimension=dim,
                user_a_response=user_a_answers[q_key],
                user_b_response=user_b_answers[q_key],
                delta=delta,
                topic=f"Question {q_num}"  # En producción, buscar topic real del schema
            ))

        # Compatibility score (0-100)
        # 100 = sin desacuerdos (todos delta 0)
        # 0 = máximo desacuerdo (todos delta 4)
        avg_delta_all = sum(deltas.values()) / len(deltas) if deltas else 0
        compatibility_score = max(0, 100 - int(avg_delta_all * 25))  # 0-4 → 100-0

        # Metadata
        metadata = {
            "user_a_avg_response": round(sum(user_a_answers.values()) / len(user_a_answers), 2),
            "user_b_avg_response": round(sum(user_b_answers.values()) / len(user_b_answers), 2),
            "total_perfect_agreement": sum(1 for d in deltas.values() if d == 0),
            "total_max_disagreement": sum(1 for d in deltas.values() if d == 4),
        }

        return FrictionMap(
            couple_id=couple_id,
            dimension_frictions=dimension_frictions,
            top_friction_questions=top_friction,
            compatibility_score=compatibility_score,
            total_questions=len(deltas),
            metadata=metadata
        )

    def get_dimension_by_question(self, question_num: int) -> Optional[Dimension]:
        """Obtiene la dimensión de una pregunta"""
        q_key = f"q{question_num}"
        dim_str = self.question_dimensions.get(q_key)
        if dim_str:
            try:
                return Dimension(dim_str)
            except ValueError:
                return None
        return None


# ============ CONTRADICTIONS & NARRATIVES ============

@dataclass
class Contradiction:
    """Detecta contradicción entre autopercepción y datos"""
    dimension: Dimension
    narrative: str                      # Texto empático pero implacable
    severity: str                       # "critical" | "high" | "moderate"
    user_perception: float              # Autopercepción (1-5 ej: estrés bajo)
    actual_data: float                  # Dato real (ej: 18h/semana de tareas)


@dataclass
class QuickWin:
    """Una tarea específica, accionable inmediatamente"""
    week: int                           # 1-4
    day: str                            # "Monday", "Wednesday"
    time: str                           # "09:00 AM"
    task: str                           # Tarea ultra-específica
    impact: str                         # "high" | "medium"
    effort_hours: float                 # Tiempo estimado
    expected_outcome: str               # Resultado esperado


@dataclass
class QuickWinsPlan:
    """Plan de 4 semanas de acciones"""
    weeks: List[List[QuickWin]]         # 4 semanas × N tareas/semana
    total_effort_hours: float
    estimated_impact_annual: str        # "€ ahorrados/generados por año"


@dataclass
class COICalculation:
    """Cost of Inaction: pérdidas financieras estimadas"""
    vampire_expenses_annual: float      # Gastos duplicados, suscripciones
    opportunity_cost_inflation: float   # Capital parado perdiendo valor
    time_waste_value: float             # Horas delegables × tarifa horaria
    total_annual_loss: float            # Suma total
    five_year_projection: float         # Total × 5 años

    @property
    def formatted_annual(self) -> str:
        return f"{self.total_annual_loss:,.0f} €/año"

    @property
    def formatted_five_years(self) -> str:
        return f"{self.five_year_projection:,.0f} €"


@dataclass
class ArchetypeProfile:
    """Arquetipo detectado basado en cruce de dimensiones"""
    name: str                           # Ej: "Hogar de Alta Ingesta con Fuga Patrimonial"
    profile_icon: str                   # Emoji o símbolo visual
    description: str                    # Párrafo de 2-3 líneas
    strengths: List[str]                # Top 3 fortalezas
    vulnerabilities: List[str]          # Top 3 vulnerabilidades


# ============ INSIGHTS & NARRATIVES ============

class FrictionInsights:
    """Genera insights texto, contradicciones y narrativa empática"""

    @staticmethod
    def generate_executive_summary(friction_map: FrictionMap, archetype: ArchetypeProfile) -> str:
        """Genera resumen ejecutivo de fricción (lectura 3 minutos)"""
        score = friction_map.compatibility_score

        if score >= 80:
            tone = "excelente"
        elif score >= 60:
            tone = "buena"
        elif score >= 40:
            tone = "requiere trabajo"
        else:
            tone = "crítica"

        summary = f"""
COMPATIBILITY SCORE: {score}/100 ({tone})

Arquetipo Detectado: {archetype.name}

Compatible en: {friction_map.metadata.get('total_perfect_agreement', 0)} preguntas
Máximo desacuerdo en: {friction_map.metadata.get('total_max_disagreement', 0)} preguntas

Áreas más armónicas: {max(friction_map.dimension_frictions.items(), key=lambda x: 100 - (x[1].avg_delta * 25))[0]}
Áreas de fricción: {max(friction_map.dimension_frictions.items(), key=lambda x: x[1].avg_delta)[0]}
        """.strip()

        return summary

    @staticmethod
    def detect_contradictions(
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int],
        friction_map: FrictionMap
    ) -> List[Contradiction]:
        """
        Detecta contradicciones entre autopercepción y datos.
        Ej: "Dices que el estrés es bajo, pero trabajas 60h/semana"

        Returns:
            Lista de Contradiction ordenadas por severity
        """
        contradictions = []

        # Dimensión por dimensión
        for dim_code, dim_friction in friction_map.dimension_frictions.items():
            dim = dim_friction.dimension

            # Heurística: si responden "bajo" en autopercepción pero tienen alta fricción
            # = contradicción
            if dim_friction.avg_delta >= 2.5:  # Alta fricción
                # Simulación: buscar respuesta baja en pregunta de autopercepción
                # En producción: mappear exact question IDs
                avg_response = (
                    sum(user_a_answers.values()) +
                    sum(user_b_answers.values())
                ) / (len(user_a_answers) + len(user_b_answers))

                if avg_response <= 2:  # Respuesta baja
                    narrative = f"Tu autopercepción de {dim.value} es baja ({avg_response:.1f}/5), " \
                               f"sin embargo, tus datos indican fricción alta ({dim_friction.avg_delta:.1f}/4). " \
                               f"Existe una normalización del problema que está afectando silenciosamente tu relación."

                    contradictions.append(Contradiction(
                        dimension=dim,
                        narrative=narrative,
                        severity="critical",
                        user_perception=avg_response,
                        actual_data=dim_friction.avg_delta
                    ))

        return sorted(contradictions, key=lambda x: {"critical": 0, "high": 1, "moderate": 2}.get(x.severity, 3))

    @staticmethod
    def friction_critical_alerts(friction_map: FrictionMap) -> List[str]:
        """Genera alertas críticas (alto riesgo a corto plazo)"""
        alerts = []

        for dim_friction in friction_map.dimension_frictions.values():
            if dim_friction.avg_delta >= 3.0:  # Desacuerdo extremo
                alerts.append(
                    f"🚨 ALERTA CRÍTICA en {dim_friction.dimension.value}: "
                    f"desacuerdo promedio {dim_friction.avg_delta:.1f}/4. "
                    f"Este nivel de fricción requiere intervención inmediata."
                )

        return alerts if alerts else []


# ============ QUICK WINS PLANNER ============

class QuickWinsPlanner:
    """Genera plan de 4 semanas con tareas ultra-específicas"""

    @staticmethod
    def generate_4week_plan(
        friction_map: FrictionMap,
        archetype: ArchetypeProfile
    ) -> QuickWinsPlan:
        """
        Genera plan de 4 semanas ordenado por impacto/esfuerzo.
        Cada tarea es tan específica que se puede ejecutar mañana a las 09:00 AM.

        Returns:
            QuickWinsPlan con 4 semanas de tareas
        """
        all_weeks = [[], [], [], []]
        total_hours = 0

        # Semana 1: Identificación y automatización rápida
        week1_tasks = [
            QuickWin(
                week=1,
                day="Monday",
                time="09:00 AM",
                task="Auditoría de suscripciones: revisar últimos 3 extractos bancarios y listar todos los servicios recurrentes duplicados.",
                impact="high",
                effort_hours=0.5,
                expected_outcome="Identificar 3-5 suscripciones cancelables"
            ),
            QuickWin(
                week=1,
                day="Wednesday",
                time="15:00 PM",
                task="Cancelar servicios duplicados (streaming, apps, softwares) y reasignar presupuesto a fondo de inversión.",
                impact="high",
                effort_hours=0.75,
                expected_outcome="Liberar 50-150€/mes"
            ),
            QuickWin(
                week=1,
                day="Friday",
                time="18:00 PM",
                task="Configurar transferencia automática del 10% de nómina a cuenta de fondo indexado (día de cobro).",
                impact="high",
                effort_hours=0.5,
                expected_outcome="Automatizar ahorro de 150-500€/mes sin fricción"
            ),
        ]

        # Semana 2: Comunicación y distribución de carga
        week2_tasks = [
            QuickWin(
                week=2,
                day="Monday",
                time="19:00 PM",
                task="Reunión familiar en mesa: inventariar todas las tareas domésticas semanales (duración, responsable actual, carga).",
                impact="high",
                effort_hours=1.0,
                expected_outcome="Mapa visual de la sobrecarga en una persona"
            ),
            QuickWin(
                week=2,
                day="Wednesday",
                time="20:00 PM",
                task="Redistribuir 3 tareas más pesadas entre miembros del hogar según capacidad y horarios.",
                impact="high",
                effort_hours=1.5,
                expected_outcome="Reducir sobrecarga del sustentador principal en 8-10h/semana"
            ),
        ]

        # Semana 3: Validación de seguridad
        week3_tasks = [
            QuickWin(
                week=3,
                day="Tuesday",
                time="10:00 AM",
                task="Revisar pólizas de seguro: vida, salud, inmueble. Identificar brechas (ej: sin fondo de emergencia).",
                impact="high",
                effort_hours=1.0,
                expected_outcome="Validar cobertura o identificar brechas críticas"
            ),
            QuickWin(
                week=3,
                day="Thursday",
                time="14:00 PM",
                task="Si falta: solicitar presupuesto de seguros para cerrar brechas identificadas.",
                impact="medium",
                effort_hours=0.75,
                expected_outcome="Protección familiar completa"
            ),
        ]

        # Semana 4: Seguimiento y optimización
        week4_tasks = [
            QuickWin(
                week=4,
                day="Monday",
                time="09:00 AM",
                task="Revisar estado de cambios (automatizaciones activas, redistribución de tareas, nuevos ahorros).",
                impact="medium",
                effort_hours=0.5,
                expected_outcome="Confirmar que cambios están implementados y funcionan"
            ),
            QuickWin(
                week=4,
                day="Friday",
                time="17:00 PM",
                task="Sesión de cierre: evaluar el impacto inicial, ajustar si es necesario, planificar siguientes meses.",
                impact="medium",
                effort_hours=1.0,
                expected_outcome="Hoja de ruta para los próximos 3 meses"
            ),
        ]

        all_weeks[0] = week1_tasks
        all_weeks[1] = week2_tasks
        all_weeks[2] = week3_tasks
        all_weeks[3] = week4_tasks

        total_hours = sum(
            task.effort_hours
            for week in all_weeks
            for task in week
        )

        return QuickWinsPlan(
            weeks=all_weeks,
            total_effort_hours=total_hours,
            estimated_impact_annual="1.200 - 3.600 €"
        )


# ============ COST OF INACTION (COI) ============

class COICalculator:
    """Calcula el coste real de mantener los hábitos actuales"""

    @staticmethod
    def estimate_coi(
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int],
        friction_map: FrictionMap
    ) -> COICalculation:
        """
        Estima pérdidas anuales y proyección a 5 años.
        Combina: gastos vampiro, oportunidad de inflación, tiempo basura.

        Returns:
            COICalculation con estimaciones
        """
        # 1. GASTOS VAMPIRO (suscripciones duplicadas, servicios innecesarios)
        # Heurística: baja respuesta en "presupuesto controlado" = gastos vampiro
        avg_all = (
            sum(user_a_answers.values()) +
            sum(user_b_answers.values())
        ) / (len(user_a_answers) + len(user_b_answers))

        # Si promedio bajo = muchos gastos incontrolados
        vampire_expenses_annual = max(0, (5 - avg_all) * 300)  # Escala de 0-1200€

        # 2. OPORTUNIDAD DE INFLACIÓN
        # Si declaran capital parado en cuenta corriente = pérdida por inflación
        # Heurística: suma presupuesto bajo = capital mal invertido
        capital_parado_estimated = max(5000, avg_all * 10000)  # Entre 5k-50k
        inflation_rate = 0.03  # 3% anual
        opportunity_cost_inflation = capital_parado_estimated * inflation_rate

        # 3. COSTE DEL TIEMPO BASURA (horas delegables)
        # Heurística: fricción alta en domesticity = muchas horas de tareas
        high_friction_dimension = max(
            friction_map.dimension_frictions.items(),
            key=lambda x: x[1].avg_delta
        )[1]

        if high_friction_dimension.avg_delta >= 2.5:
            # Alto desacuerdo en doméstico = sobrecarga
            estimated_wasted_hours_weekly = 12  # 12h/semana de tareas delegables
            hourly_rate_estimate = 40  # €/hora (estimar de ingresos)
            time_waste_value = estimated_wasted_hours_weekly * 52 * hourly_rate_estimate
        else:
            time_waste_value = 0

        # TOTAL
        total_annual_loss = vampire_expenses_annual + opportunity_cost_inflation + time_waste_value
        five_year_projection = total_annual_loss * 5

        return COICalculation(
            vampire_expenses_annual=vampire_expenses_annual,
            opportunity_cost_inflation=opportunity_cost_inflation,
            time_waste_value=time_waste_value,
            total_annual_loss=total_annual_loss,
            five_year_projection=five_year_projection
        )


# ============ ARCHETYPE DETECTION ============

@dataclass
class FODAQuadrant:
    """Un cuadrante del FODA (Fortaleza, Oportunidad, Debilidad, Amenaza)"""
    title: str                          # Ej: "Tus Fugas de Control"
    narrative: str                      # Párrafo de 3-4 líneas
    items: List[str]                    # 3-5 bullets específicos
    icon: str                           # Visual emoji
    actionable: bool                    # True si el usuario puede actuar sobre esto


@dataclass
class FODAMatrix:
    """Matriz FODA completa (4 cuadrantes + cruce estratégico)"""
    weaknesses: FODAQuadrant            # Interno, usuario responsable
    threats: FODAQuadrant               # Externo, riesgos sistémicos
    strengths: FODAQuadrant             # Interno, validación de logros
    opportunities: FODAQuadrant         # Externo, potencial no explotado
    strategic_coherence: str            # Sección de cruce: "Estrategia de Supervivencia Familiar"


# ============ ARCHETYPE DETECTION ============

class ArchetypeDetector:
    """Detecta arquetipo familiar basado en dimensiones"""

    ARCHETYPES = {
        "high_income_low_control": ArchetypeProfile(
            name="Hogar de Alta Ingesta con Fuga Patrimonial",
            profile_icon="💰→💨",
            description="Generan ingresos significativos pero carecen de control sobre gastos e inversiones.",
            strengths=["Capacidad de ingresos", "Flexibilidad laboral", "Acceso a crédito"],
            vulnerabilities=["Fuga de capital", "Gastos vampiro descontrolados", "Falta de visión patrimonial"]
        ),
        "balanced_stable": ArchetypeProfile(
            name="Familia Balanceada en Estabilidad",
            profile_icon="⚖️✅",
            description="Equilibrio en dimensiones financieras y emocionales. Base sólida para crecimiento.",
            strengths=["Estabilidad emocional", "Presupuesto controlado", "Comunicación clara"],
            vulnerabilities=["Potencial de crecimiento no explotado", "Conservadurismo en inversiones"]
        ),
        "time_poor_capital_rich": ArchetypeProfile(
            name="Familia Saturada: Capital pero Sin Tiempo",
            profile_icon="⏳💵",
            description="Poseen capital y seguridad pero están sobrecargados en tiempo y energía doméstica.",
            strengths=["Seguridad financiera", "Patrimonio estable", "Ingresos diversificados"],
            vulnerabilities=["Agotamiento relacional", "Tareas domésticas ineficientes", "Ausencia de tiempo de pareja"]
        ),
    }

    @staticmethod
    def detect(friction_map: FrictionMap) -> ArchetypeProfile:
        """
        Detecta el arquetipo de la familia basándose en el patrón de fricción.

        Returns:
            ArchetypeProfile matching
        """
        dims = friction_map.dimension_frictions

        finances_delta = dims.get("finances", DimensionFriction(
            Dimension.FINANCES, [], 0, 0, []
        )).avg_delta
        patrimony_delta = dims.get("patrimony", DimensionFriction(
            Dimension.PATRIMONY, [], 0, 0, []
        )).avg_delta
        robustness_delta = dims.get("robustness", DimensionFriction(
            Dimension.ROBUSTNESS, [], 0, 0, []
        )).avg_delta

        # Lógica de detección
        if finances_delta > 2.0 and patrimony_delta > 2.0:
            return ArchetypeDetector.ARCHETYPES["high_income_low_control"]
        elif finances_delta < 1.5 and patrimony_delta < 1.5 and robustness_delta < 1.5:
            return ArchetypeDetector.ARCHETYPES["balanced_stable"]
        else:
            return ArchetypeDetector.ARCHETYPES["time_poor_capital_rich"]


# ============ DIAGNOSTIC ENGINEERING — LEVEL WORLD CLASS ============

@dataclass
class CurrentState:
    """Fotografía real de la familia basada en respuestas"""
    monthly_fixed_expenses_pct: float                    # % ingresos en gastos fijos (ej: 85%)
    weekly_household_hours: float                        # Horas semanales en logística doméstica
    stress_level_1_5: float                             # Nivel de estrés psicosomático (1-5)
    external_patrimony_euros: float                      # Patrimonio fuera del hogar (0€, 50k€, etc)
    emergency_fund_months: int                          # Meses de cobertura
    income_stability: str                               # "estable", "vulnerable", "crítica"
    relationship_discussions_monthly: int               # Discusiones por dinero/mes
    description_narrative: str                          # "Gastos fijos al 85%..."


@dataclass
class IdealState:
    """Horizonte anhelado — aspiraciones extraídas de open answers"""
    freedom_of_agenda: bool                             # ¿Libertad de agenda?
    emergency_buffer_months: int                        # Colchón deseado (ej: 12 meses)
    educational_fund_euros: float                       # Fondo educativo objetivo (ej: 50k€)
    stress_target_1_5: float                           # Estrés deseado (ej: 1.5/5)
    family_quality_of_life_descriptor: str             # "Tiempo en familia sin culpa", "Viajes sin presión", etc
    description_narrative: str                          # "Libertad de agenda, colchón de 12 meses..."


@dataclass
class DeviationIndex:
    """Índice de Desviación del Destino (IDD)"""
    deviation_percentage: float                         # 0-100%: qué tan lejos está de la meta
    trajectory_assessment: str                          # "Necesita corrección inmediata" / "En camino" / "Adelantado"
    time_to_crisis_months: int                         # Meses hasta agotamiento biológico/crisis
    critical_narrative: str                            # "Estás 68% desviado..."


@dataclass
class InvisibleBarrier:
    """Una barrera estructural/conductual/asimétrica"""
    category: str                                       # "infraestructura" | "conducta" | "asimetría"
    title: str                                         # Ej: "Falta de Estandarización del Sistema Doméstico"
    severity: str                                      # "crítica" | "alta" | "media" | "baja"
    percentage_impact: float                           # % de fatiga/ineficiencia atribuible a esta barrera
    narrative: str                                     # "Tu hogar sufre de falta de estandarización..."
    hidden_cost_annual: float                         # Coste oculto en horas/euros/bienestar


@dataclass
class DealBreakerAlert:
    """Alerta de contención inmediata — problema médico-urgente"""
    alert_type: str                                    # "solvencia" | "salud_relacional" | "colapso_psicológico"
    severity_level: int                                # 1-5: nivel de urgencia
    title: str                                         # "Punto de Quiebre: Solvencia Crítica"
    trigger_condition: str                            # "Fondo < 1 mes" / "Discusiones > 3x/mes"
    immediate_action: str                             # "Se congela cualquier recomendación de inversión..."
    protocol_narrative: str                           # Párrafo de contexto médico


@dataclass
class LeveragePoint:
    """Punto de máxima palanca — dónde el pequeño esfuerzo genera máximo retorno"""
    dimension: str                                     # Ej: "Logística Doméstica"
    action: str                                        # Ej: "Automatizar menús y compra"
    effort_hours_week: float                          # Esfuerzo requerido
    freedom_liberated_hours_week: float               # Horas liberadas inmediatamente
    downstream_impact: str                            # Ej: "Claridad para reestructurar deuda"
    months_to_compound_effect: int                    # Meses hasta que se nota el efecto dominó
    narrative: str                                    # "No intentes arreglar tus inversiones..."


@dataclass
class FamilyAlignmentAct:
    """Acta de Alineación Estratégica — documento vinculante emocional"""
    family_name: str
    assessment_date: str
    three_key_commitments: List[str]                 # 3 compromisos acordados
    commitment_period_months: int                    # Plazo de revisión (ej: 6 meses)
    signature_lines: Dict[str, str]                 # {"user_a_name": "", "user_b_name": ""}
    witness_line: str                                # Adaptador o testigo (Javier/Bea)
    formal_statement: str                            # Párrafo de solemnidad
    next_review_date: str                           # Fecha de revisión


# ============ DYNAMIC FODA MATRIX ============

class FODACalculator:
    """
    Calcula la Matriz FODA Dinámica e Hiper-personalizada.

    No es un cuadro genérico: es una radiografía matemática cruzada por IA.
    Cada cuadrante se rellena con datos reales de las 500 respuestas.
    """

    @staticmethod
    def calculate_foda(
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int],
        friction_map: FrictionMap,
        coi: COICalculation,
        archetype: ArchetypeProfile
    ) -> FODAMatrix:
        """
        Calcula los 4 cuadrantes FODA + sección de cruce estratégico.

        Returns:
            FODAMatrix completa, lista para PDF
        """

        # ============ DEBILIDADES (Interno - Usuario responsable) ============
        weaknesses_items = []
        weaknesses_narrative = ""

        dims = friction_map.dimension_frictions
        finances_avg = dims.get("finances", DimensionFriction(Dimension.FINANCES, [], 0, 0, [])).avg_delta
        robustness_avg = dims.get("robustness", DimensionFriction(Dimension.ROBUSTNESS, [], 0, 0, [])).avg_delta

        if coi.vampire_expenses_annual > 200:
            weaknesses_items.append(
                f"Fuga mensual de {coi.vampire_expenses_annual/12:.0f}€ en gastos vampiro "
                f"(suscripciones duplicadas, compras por impulso, servicios no utilizados)."
            )

        if robustness_avg > 2.0:
            weaknesses_items.append(
                f"Asimetría en carga mental: un miembro soporta {robustness_avg*20:.0f}% más responsabilidad "
                f"que el otro en decisiones familiares críticas."
            )

        if coi.opportunity_cost_inflation > 150:
            weaknesses_items.append(
                f"Capital parado en cuenta corriente ({coi.capital_parado_estimated:,.0f}€) "
                f"perdiendo {coi.opportunity_cost_inflation:.0f}€/año a inflación sin protección."
            )

        if finances_avg > 1.5:
            weaknesses_items.append(
                "Falta de protocolo de contención de gasto mensual. Ausencia de presupuesto compartido."
            )

        weaknesses_narrative = (
            f"Tu capacidad de generación de ingresos es alta, pero tu Dimensión II (Finanzas) revela "
            f"un {coi.vampire_expenses_annual/sum(user_a_answers.values())*100:.0f}% de fuga en gastos incontrolados. "
            f"Tu principal debilidad es la falta de un protocolo de contención de gasto mensual. "
            f"Es accionable: depende 100% de ti implementar cambios esta semana."
        )

        weaknesses = FODAQuadrant(
            title="🛑 TUS FUGAS DE CONTROL",
            narrative=weaknesses_narrative,
            items=weaknesses_items[:4],
            icon="🛑",
            actionable=True
        )

        # ============ AMENAZAS (Externo - Riesgos sistémicos) ============
        threats_items = []
        threats_narrative = ""

        # Heurística: detectar dependencia de una nómina
        single_income_ratio = 0.9  # Asumir 90% dependencia si es un usuario solo
        emergency_fund_months = 2  # Asumir < 3 meses si capital bajo

        threats_items.append(
            f"Dependencia de fuente única de ingresos ({single_income_ratio*100:.0f}%). "
            f"Rescisión, reestructuración o enfermedad laboral crearían crisis financiera inmediata."
        )

        threats_items.append(
            f"Fondo de emergencia insuficiente ({emergency_fund_months} meses vs. recomendado 6). "
            f"Cualquier gasto imprevisto (reparación, enfermedad) forzaría endeudamiento."
        )

        threats_items.append(
            f"Exposición directa a IPC sin cobertura: tu poder adquisitivo se erosiona {0.03*100:.0f}% anual "
            f"en capital parado. A 5 años: -{coi.opportunity_cost_inflation*5:,.0f}€."
        )

        threats_items.append(
            "Sector laboral vulnerable a disruption tecnológica o cambios macroeconómicos. "
            "Sin plan B de ingresos alternativos."
        )

        threats_narrative = (
            f"Al depender en un {single_income_ratio*100:.0f}% de una única nómina y tener un fondo de emergencia "
            f"de {emergency_fund_months} meses, tu hogar se encuentra en riesgo crítico ante rescisión contractual "
            f"o cambio macroeconómico. Son riesgos externos que NO controlas, pero CUya mitigación sí depende de acciones "
            f"que puedes iniciar hoy: diversificar ingresos y construir colchón de emergencia."
        )

        threats = FODAQuadrant(
            title="⚡ TUS PUNTOS DE VULNERABILIDAD ALERTA ROJA",
            narrative=threats_narrative,
            items=threats_items[:4],
            icon="⚡",
            actionable=False  # Externo, pero mitigable
        )

        # ============ FORTALEZAS (Interno - Validación de logros) ============
        strengths_items = []
        strengths_narrative = ""

        conciliation_avg = dims.get("conciliation", DimensionFriction(Dimension.CONCILIATION, [], 0, 0, [])).avg_delta
        psychology_avg = dims.get("psychology", DimensionFriction(Dimension.PSYCHOLOGY, [], 0, 0, [])).avg_delta

        if conciliation_avg < 1.5:
            strengths_items.append(
                f"Alineación en objetivos de vida a largo plazo (Dimensión I: acuerdo {100-conciliation_avg*25:.0f}%). "
                f"Visión compartida es tu mayor activo para implementar cambios."
            )

        if psychology_avg < 1.5:
            strengths_items.append(
                f"Nivel de estrés por deudas bajo (Dimensión V: {100-psychology_avg*25:.0f}% de tranquilidad). "
                f"Resiliencia emocional para enfrentar cambios sin pánico."
            )

        if sum(user_a_answers.values()) > 200 and sum(user_b_answers.values()) > 200:
            strengths_items.append(
                "Ambos miembros comprometidos con el diagnóstico. Esta toma de conciencia compartida "
                "es el 50% del éxito de cualquier cambio familiar."
            )

        if coi.vampire_expenses_annual < sum(user_a_answers.values()) * 50:
            strengths_items.append(
                f"Capacidad de ahorro bruto no despreciable: "
                f"{(sum(user_a_answers.values()) + sum(user_b_answers.values()))/2:.0f}€/mes potenciales si eliminas fugas."
            )

        strengths_narrative = (
            f"Tu Dimensión I muestra una excelente alineación de pareja respecto a los objetivos de vida a largo plazo, "
            f"y tu Dimensión V revela un nivel de estrés relacional bajo. "
            f"Tu resiliencia emocional y cohesión es tu mayor activo para implementar cambios financieros sin ruptura. "
            f"Úsalo."
        )

        strengths = FODAQuadrant(
            title="💪 TUS PILARES DE ESTABILIDAD",
            narrative=strengths_narrative,
            items=strengths_items[:4],
            icon="💪",
            actionable=True
        )

        # ============ OPORTUNIDADES (Externo - Potencial) ============
        opportunities_items = []
        opportunities_narrative = ""

        if coi.opportunity_cost_inflation > 200:
            capital_10y = coi.capital_parado_estimated * ((1 + 0.07) ** 10)  # 7% CAGR fondos indexados
            opportunities_items.append(
                f"Tu excedente mensual de {coi.vampire_expenses_annual/12:.0f}€ automatizado en Fondos Indexados "
                f"proyecta {capital_10y:,.0f}€ en 10 años (vs. {coi.capital_parado_estimated:,.0f}€ hoy perdiendo valor)."
            )

        opportunities_items.append(
            "Tipos de interés históricos favorables para refinanciamiento de deudas. "
            "Si tienes hipoteca o préstamos a tipo fijo antiguo, oportunidad de ahorro."
        )

        opportunities_items.append(
            "Mercado de educación online en crecimiento: potencial de diversificación de ingresos "
            "vendiendo expertise o cursos (relaja dependencia de nómina)."
        )

        opportunities_items.append(
            "Productos de seguros de vida y discapacidad asequibles actualmente. "
            "Protege tu fortaleza (cohesión de pareja) de amenazas externas (pérdida de sustentador)."
        )

        opportunities_narrative = (
            f"Dado que dispones de un excedente mensual potencial de {coi.vampire_expenses_annual/12:.0f}€ "
            f"(una vez elimines fugas) y una cohesión familiar sólida, la situación actual del mercado te ofrece "
            f"la oportunidad de automatizar aportaciones a Fondos Indexados. "
            f"Proyección: construcción de {capital_10y:,.0f}€ de patrimonio en 10 años utilizando interés compuesto. "
            f"Es el momento: tipos de interés están cambiando."
        )

        opportunities = FODAQuadrant(
            title="🚀 TU VENTANA DE CRECIMIENTO PATRIMONIAL",
            narrative=opportunities_narrative,
            items=opportunities_items[:4],
            icon="🚀",
            actionable=True
        )

        # ============ STRATEGIC COHERENCE (Cruce de los 4 cuadrantes) ============
        strategic_coherence = (
            f"ESTRATEGIA DE SUPERVIVENCIA FAMILIAR:\n\n"
            f"Para mitigar tu AMENAZA (dependencia de una única nómina) debes utilizar tu FORTALEZA "
            f"(cohesión de pareja y bajo estrés relacional) para corregir tu DEBILIDAD (dinero muerto perdiendo valor) "
            f"y ejecutar la OPORTUNIDAD (automatizar inversión en Fondos Indexados esta misma semana).\n\n"
            f"Secuencia exacta de 4 semanas:\n"
            f"1. Cancelar servicios duplicados (liberan {coi.vampire_expenses_annual/12:.0f}€/mes)\n"
            f"2. Automatizar transferencia del 10% a Fondo Indexado (día de cobro)\n"
            f"3. Crear fondo de emergencia en 6 meses (tu almohada contra rescisión)\n"
            f"4. Explorar fuentes de ingreso alternativas (relaja dependencia de nómina única)\n\n"
            f"Impacto en 5 años: {coi.five_year_projection:,.0f}€ destruidos si NO actúas vs. "
            f"+{capital_10y:,.0f}€ construidos si actúas HOY."
        )

        return FODAMatrix(
            weaknesses=weaknesses,
            threats=threats,
            strengths=strengths,
            opportunities=opportunities,
            strategic_coherence=strategic_coherence
        )


# ============ ENGINEERING: CURRENT STATE ANALYSIS ============

class CurrentStateAnalyzer:
    """Fotografía real de la familia — traducción de respuestas a métricas"""

    @staticmethod
    def analyze(
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int],
        friction_map: FrictionMap,
        coi: COICalculation
    ) -> CurrentState:
        """
        Extrae la Fotografía Real de la familia.

        Basado en:
        - Respuestas de presupuesto y gastos (Q1-Q50)
        - Respuestas de tiempo doméstico (Q51-Q100)
        - Respuestas de estrés relacional (Q401-Q500)
        """

        avg_answers = (sum(user_a_answers.values()) + sum(user_b_answers.values())) / 2

        # Estimación de gastos fijos % (inversamente correlacionado con Q40-Q50 sobre austeridad)
        budget_control_q40_50 = sum(
            [user_a_answers.get(f"q{i}", 3) for i in range(40, 51)]
        ) / 11 + sum(
            [user_b_answers.get(f"q{i}", 3) for i in range(40, 51)]
        ) / 11
        monthly_fixed_expenses_pct = max(55, 100 - (budget_control_q40_50 * 5))

        # Estimación horas domésticas semanales (Q51-Q100)
        household_q51_100_a = sum(
            [user_a_answers.get(f"q{i}", 3) for i in range(51, 101)]
        ) / 50
        household_q51_100_b = sum(
            [user_b_answers.get(f"q{i}", 3) for i in range(51, 101)]
        ) / 50
        weekly_household_hours = ((6 - household_q51_100_a) + (6 - household_q51_100_b)) * 5

        # Estrés psicosomático (Q401-Q450, inversamente escalado)
        stress_q_a = sum(
            [user_a_answers.get(f"q{i}", 3) for i in range(401, 451)]
        ) / 50
        stress_q_b = sum(
            [user_b_answers.get(f"q{i}", 3) for i in range(401, 451)]
        ) / 50
        stress_level_1_5 = 6 - ((stress_q_a + stress_q_b) / 2)

        # Patrimonio externo (estimado de Q200-Q250)
        patrimony_q = sum(
            [user_a_answers.get(f"q{i}", 1) for i in range(200, 251)]
        ) / 50
        external_patrimony_euros = max(0, (patrimony_q - 1) * 25000)

        # Fondo de emergencia (estimado de respuestas sobre ahorros)
        emergency_fund_months = max(1, monthly_fixed_expenses_pct // 20)

        # Income stability (de Q101-Q150, preguntas sobre ingresos)
        income_stability_q = sum(
            [user_a_answers.get(f"q{i}", 3) for i in range(101, 151)]
        ) / 50
        if income_stability_q < 2:
            income_stability = "crítica"
        elif income_stability_q < 3.5:
            income_stability = "vulnerable"
        else:
            income_stability = "estable"

        # Discusiones mensuales por dinero (de Q451-Q500)
        discussions_q_a = sum(
            [user_a_answers.get(f"q{i}", 1) for i in range(451, 501)]
        ) / 50
        discussions_q_b = sum(
            [user_b_answers.get(f"q{i}", 1) for i in range(451, 501)]
        ) / 50
        relationship_discussions_monthly = int(
            ((6 - discussions_q_a) + (6 - discussions_q_b)) / 2
        )

        description_narrative = (
            f"Gastos fijos al {monthly_fixed_expenses_pct:.0f}% de ingresos, "
            f"{weekly_household_hours:.1f} horas semanales en logística doméstica, "
            f"nivel de estrés psicosomático de {stress_level_1_5:.1f}/5, "
            f"patrimonio externo: {external_patrimony_euros:,.0f}€, "
            f"fondo de emergencia: {emergency_fund_months} meses, "
            f"estabilidad de ingresos: {income_stability}, "
            f"discusiones sobre dinero: {relationship_discussions_monthly}x/mes."
        )

        return CurrentState(
            monthly_fixed_expenses_pct=monthly_fixed_expenses_pct,
            weekly_household_hours=weekly_household_hours,
            stress_level_1_5=stress_level_1_5,
            external_patrimony_euros=external_patrimony_euros,
            emergency_fund_months=emergency_fund_months,
            income_stability=income_stability,
            relationship_discussions_monthly=relationship_discussions_monthly,
            description_narrative=description_narrative
        )


# ============ ENGINEERING: IDEAL STATE EXTRACTION ============

class IdealStateExtractor:
    """Horizonte anhelado — aspiraciones desde open answers"""

    @staticmethod
    def extract(user_a_answers: Dict[str, int], user_b_answers: Dict[str, int]) -> IdealState:
        """
        Extrae aspiraciones desde respuestas abiertas y preguntas de proyección.

        Nota: En este MVP, usa heurísticas basadas en niveles de respuesta.
        En producción, se procesaría NLP sobre open_answers_encrypted.
        """

        # Freedom of agenda (de respuestas sobre tiempo flexible)
        freedom_q = (
            sum([user_a_answers.get(f"q{i}", 3) for i in range(151, 176)]) / 25 +
            sum([user_b_answers.get(f"q{i}", 3) for i in range(151, 176)]) / 25
        ) / 2
        freedom_of_agenda = freedom_q > 3.5

        # Colchón deseado (de respuestas sobre seguridad)
        safety_q = (
            sum([user_a_answers.get(f"q{i}", 3) for i in range(176, 201)]) / 25 +
            sum([user_b_answers.get(f"q{i}", 3) for i in range(176, 201)]) / 25
        ) / 2
        emergency_buffer_months = int(6 + (safety_q - 3) * 6)

        # Fondo educativo (de preguntas sobre hijos/educación)
        education_q = (
            sum([user_a_answers.get(f"q{i}", 2) for i in range(251, 276)]) / 25 +
            sum([user_b_answers.get(f"q{i}", 2) for i in range(251, 276)]) / 25
        ) / 2
        educational_fund_euros = int(20000 + (education_q - 2) * 10000)

        # Estrés deseado (inversamente escalado)
        stress_q = (
            sum([user_a_answers.get(f"q{i}", 3) for i in range(301, 326)]) / 25 +
            sum([user_b_answers.get(f"q{i}", 3) for i in range(301, 326)]) / 25
        ) / 2
        stress_target_1_5 = max(1.0, 3.5 - (stress_q - 3) * 0.5)

        family_quality_of_life_descriptor = (
            "Tiempo en familia sin culpa, viajes sin presión, "
            "libertad de elegir horarios, transiciones sin prisa"
        )

        description_narrative = (
            f"Libertad de agenda: {freedom_of_agenda}, "
            f"colchón de emergencia: {emergency_buffer_months} meses, "
            f"fondo educativo: {educational_fund_euros:,.0f}€, "
            f"estrés objetivo: {stress_target_1_5:.1f}/5, "
            f"calidad de vida: {family_quality_of_life_descriptor}."
        )

        return IdealState(
            freedom_of_agenda=freedom_of_agenda,
            emergency_buffer_months=emergency_buffer_months,
            educational_fund_euros=educational_fund_euros,
            stress_target_1_5=stress_target_1_5,
            family_quality_of_life_descriptor=family_quality_of_life_descriptor,
            description_narrative=description_narrative
        )


# ============ ENGINEERING: DEVIATION INDEX ============

class DeviationIndexCalculator:
    """Índice de Desviación del Destino (IDD) — qué tan lejos está de la meta"""

    @staticmethod
    def calculate(
        current_state: CurrentState,
        ideal_state: IdealState,
        coi: COICalculation,
        friction_map: FrictionMap
    ) -> DeviationIndex:
        """
        Calcula el IDD: porcentaje de desviación de la trayectoria.

        Fórmula:
        - Gap de gastos: (fixed_expenses_pct - 40%) / 60 = % overrun
        - Gap de tiempo: (weekly_household_hours - 8) / 15 = % overload
        - Gap de estrés: (stress_actual - stress_target) / 4 = % gap
        - Gap de patrimonio: (patrimony_actual - patrimony_target) / patrimony_target = % shortfall

        IDD = promedio ponderado de 4 gaps
        """

        # Gap de gastos (40% es el benchm ark)
        expense_gap = min(
            1.0, max(0, (current_state.monthly_fixed_expenses_pct - 40) / 60)
        )

        # Gap de tiempo (8h es benchmark sostenible)
        time_gap = min(
            1.0,
            max(0, (current_state.weekly_household_hours - 8) / 15)
        )

        # Gap de estrés (escala 1-5)
        stress_gap = min(
            1.0,
            max(
                0,
                (current_state.stress_level_1_5 - ideal_state.stress_target_1_5) / 4
            ),
        )

        # Gap de patrimonio (educacional + emergencia)
        target_patrimony = (
            ideal_state.educational_fund_euros +
            (ideal_state.emergency_buffer_months * current_state.monthly_fixed_expenses_pct * 1000)
        )
        current_patrimony = current_state.external_patrimony_euros + 5000  # baseline
        patrimony_gap = min(
            1.0,
            max(0, (target_patrimony - current_patrimony) / target_patrimony)
        )

        # IDD ponderado
        deviation_percentage = (
            (expense_gap * 0.35) +
            (time_gap * 0.25) +
            (stress_gap * 0.20) +
            (patrimony_gap * 0.20)
        ) * 100

        # Trayectoria
        if deviation_percentage > 50:
            trajectory_assessment = "Necesita corrección inmediata"
        elif deviation_percentage > 25:
            trajectory_assessment = "Desviación significativa"
        else:
            trajectory_assessment = "En camino"

        # Tiempo a crisis (en meses, basado en COI y stress)
        months_to_crisis = max(
            1,
            int(12 - (current_state.stress_level_1_5 * 2) - (coi.total_annual_loss / 3000))
        )

        critical_narrative = (
            f"Estás un {deviation_percentage:.0f}% desviado de la trayectoria necesaria "
            f"para alcanzar tu Estado Ideal en los próximos 5 años. "
            f"Si mantienes el sistema actual, llegarás al agotamiento biológico "
            f"en aproximadamente {months_to_crisis} meses."
        )

        return DeviationIndex(
            deviation_percentage=deviation_percentage,
            trajectory_assessment=trajectory_assessment,
            time_to_crisis_months=months_to_crisis,
            critical_narrative=critical_narrative
        )


# ============ ENGINEERING: INVISIBLE BARRIERS ============

class InvisibleBarriersDetector:
    """Detecta las barreras estructurales, conductuales y asimétricas invisibles"""

    @staticmethod
    def detect(
        current_state: CurrentState,
        friction_map: FrictionMap,
        coi: COICalculation
    ) -> List[InvisibleBarrier]:
        """
        Clasifica las barreras en 3 categorías:
        1. Infraestructura: sistema doméstico roto
        2. Conducta: sesgos psicológicos de consumo
        3. Asimetría: carga mental desigual
        """

        barriers = []

        # BARRERA 1: Falta de Estandarización (Infraestructura)
        if current_state.weekly_household_hours > 15:
            barriers.append(
                InvisibleBarrier(
                    category="infraestructura",
                    title="Falta de Estandarización del Sistema Doméstico",
                    severity="crítica" if current_state.weekly_household_hours > 20 else "alta",
                    percentage_impact=40,
                    narrative=(
                        "Tu hogar sufre de falta de estandarización. Estás ejecutando la logística "
                        "de tu casa como una empresa de los años 80: de forma manual, reactiva y sin "
                        "herramientas de automatización. El 40% de tu fatiga mental no se debe a tu "
                        "trabajo, sino a la ineficiencia del mantenimiento de tu propia vida."
                    ),
                    hidden_cost_annual=current_state.weekly_household_hours * 52 * 25  # 25€/hora equivalente
                )
            )

        # BARRERA 2: Sesgo de Jaula de Oro (Conducta)
        if current_state.monthly_fixed_expenses_pct > 75 and coi.vampire_expenses_annual > 200:
            barriers.append(
                InvisibleBarrier(
                    category="conducta",
                    title="Sesgo de la Jaula de Oro — Indexación de Gastos",
                    severity="alta",
                    percentage_impact=30,
                    narrative=(
                        "Detectamos el 'Sesgo de la Jaula de Oro'. A medida que tus ingresos aumentan, "
                        "tus gastos fijos se indexan inmediatamente a ese crecimiento por una necesidad "
                        "inconsciente de estatus o sobrecompensación familiar. Tu barrera no es la falta "
                        "de ingresos, es la incapacidad psicológica de sostener el excedente sin quemarlo."
                    ),
                    hidden_cost_annual=coi.vampire_expenses_annual
                )
            )

        # BARRERA 3: Asimetría de Corresponsabilidad (Asimetría)
        conciliation_delta = friction_map.dimension_frictions.get(
            "conciliation", DimensionFriction(Dimension.CONCILIATION, [], 0, 0, [])
        ).avg_delta
        if conciliation_delta > 2.0:
            barriers.append(
                InvisibleBarrier(
                    category="asimetría",
                    title="Brecha de Corresponsabilidad — Carga Mental Invisible",
                    severity="crítica",
                    percentage_impact=75,
                    narrative=(
                        f"El test detecta una brecha de corresponsabilidad del {conciliation_delta * 30:.0f}% "
                        "dentro del núcleo familiar. Mientras un miembro gestiona la estrategia financiera, "
                        "el otro absorbe toda la fricción operativa diaria. Esta asimetría es una barrera "
                        "crítica: está destruyendo la energía del motor del hogar."
                    ),
                    hidden_cost_annual=current_state.weekly_household_hours * 52 * 40  # coste emocional
                )
            )

        return barriers


# ============ ENGINEERING: DEAL-BREAKER ALERTS ============

class DealBreakerDetector:
    """Detecta puntos de quiebre que requieren protocolo de contención inmediata"""

    @staticmethod
    def detect(current_state: CurrentState, coi: COICalculation) -> List[DealBreakerAlert]:
        """
        Identifica situaciones médicas de urgencia financiera/relacional.
        """

        alerts = []

        # ALERTA 1: Solvencia Crítica
        if current_state.emergency_fund_months < 1:
            alerts.append(
                DealBreakerAlert(
                    alert_type="solvencia",
                    severity_level=5,
                    title="🚨 PUNTO DE QUIEBRE: SOLVENCIA CRÍTICA",
                    trigger_condition=f"Fondo emergencia < 1 mes ({current_state.emergency_fund_months} mes)",
                    immediate_action="Se congela cualquier recomendación de inversión. Prioridad 1: construir colchón de 3 meses en 90 días.",
                    protocol_narrative=(
                        "Tu hogar está a una avería de coche o a un retraso de nómina de entrar en números rojos. "
                        "Todos los demás objetivos se ponen en espera. La única dirección válida ahora es hacia la construcción "
                        "de un fondo de emergencia de al menos 3 meses de gastos en los próximos 90 días."
                    )
                )
            )

        # ALERTA 2: Salud Relacional Crítica
        if current_state.relationship_discussions_monthly > 3:
            alerts.append(
                DealBreakerAlert(
                    alert_type="salud_relacional",
                    severity_level=4,
                    title="⚠️ ALERTA: EROSIÓN DE LA SALUD RELACIONAL",
                    trigger_condition=f"Discusiones sobre dinero {current_state.relationship_discussions_monthly}x/mes (> 3)",
                    immediate_action="Parar. Necesitáis protocolo de comunicación estructurado. Sesión de mediación recomendada.",
                    protocol_narrative=(
                        "Tu economía está erosionando tu paz familiar. El dinero se está utilizando como herramienta de control "
                        "o válvula de escape de la frustración. Sin intervención, esta erosión acabará transformando un problema financiero "
                        "en un problema relacional irreversible."
                    )
                )
            )

        # ALERTA 3: Colapso Psicológico Inminente
        if current_state.stress_level_1_5 > 4.2:
            alerts.append(
                DealBreakerAlert(
                    alert_type="colapso_psicológico",
                    severity_level=5,
                    title="🚨 PROTOCOLO DE CONTENCIÓN: ESTRÉS CRÍTICO",
                    trigger_condition=f"Nivel estrés psicosomático {current_state.stress_level_1_5:.1f}/5 (crítico)",
                    immediate_action="Iniciar plan de reducción de fricción doméstica INMEDIATAMENTE. Delegación es NO negociable.",
                    protocol_narrative=(
                        "Has sobrepasado el umbral de sostenibilidad psicosomática. Tu cuerpo está emitiendo señales de alarma. "
                        "Continuar al ritmo actual garantiza colapso emocional, burnout profesional o rotura relacional en los próximos 6 meses. "
                        "La única intervención válida es reducir carga doméstica inmediatamente, incluso a costo financiero."
                    )
                )
            )

        return alerts


# ============ ENGINEERING: LEVERAGE FACTOR ============

class LeverageFactorCalculator:
    """Calcula el punto de máxima palanca — dónde pequeño esfuerzo = máximo retorno"""

    @staticmethod
    def calculate(
        current_state: CurrentState,
        friction_map: FrictionMap,
        coi: COICalculation
    ) -> LeveragePoint:
        """
        Identifica la intervención con máximo Efecto Dominó.

        Heurística: ¿Qué libera más horas/dinero/claridad con mínimo esfuerzo?
        """

        # Si household hours > 15: máxima palanca es delegación/automatización doméstica
        if current_state.weekly_household_hours > 15:
            return LeveragePoint(
                dimension="Logística Doméstica",
                action="Automatizar menús semanales, compra online, gestión de tareas domésticas",
                effort_hours_week=4,  # Esfuerzo inicial
                freedom_liberated_hours_week=10,  # Horas liberadas
                downstream_impact="Claridad mental para optimizar negocios, reducción estrés relacional, tiempo de pareja",
                months_to_compound_effect=4,
                narrative=(
                    "No intentes arreglar tus inversiones hoy. Tu punto de máxima palanca esta semana es automatizar "
                    "los menús y la compra del hogar. Liberar esa fricción mental inicial es el único requisito para que "
                    "tengas la claridad necesaria para reestructurar tu deuda el mes que viene."
                )
            )

        # Si stress > 3.5 y discusiones > 2: máxima palanca es protocolo de comunicación
        if current_state.stress_level_1_5 > 3.5 and current_state.relationship_discussions_monthly > 2:
            return LeveragePoint(
                dimension="Comunicación Relacional",
                action="Implementar sesión semanal de 30min (lunes 19:00) para alineación financiera",
                effort_hours_week=0.5,
                freedom_liberated_hours_week=3,  # Horas recuperadas de discusiones reactivas
                downstream_impact="Reducción de conflictividad, toma de decisiones conjunta, cohesión estratégica",
                months_to_compound_effect=2,
                narrative=(
                    "Un pequeño protocolo de comunicación estructurada disuelve el 60% de las discusiones improductivas. "
                    "Eso libera energía mental para enfrentar decisiones estratégicas de verdad."
                )
            )

        # Default: máxima palanca es control de gastos vampiro
        return LeveragePoint(
            dimension="Gastos Vampiro",
            action="Auditoría de suscripciones, cancelación de servicios duplicados, automatización de ahorros",
            effort_hours_week=2,
            freedom_liberated_hours_week=4,
            downstream_impact="Liberación de 200-400€/mes para fondo emergencia o inversión indexada",
            months_to_compound_effect=1,
            narrative=(
                "Tu barrera más accesible es eliminar los 3-5 gastos hormiga que cargan tu presupuesto. "
                "En una tarde, liberas 10-15 horas/mes de estrés sobre cash flow."
            )
        )


# ============ ENGINEERING: FAMILY ALIGNMENT ACT ============

# ============ HEAVY ARTILLERY: DEUDAS / INVERSIONES / ESTILO DE VIDA ============

@dataclass
class DebtAnalysis:
    """Termómetro de la Presión Financiera — auditoría de toxicidad del apalancamiento"""
    housing_stress_rate: float                           # TAI: % ingresos en hipoteca + mantenimiento
    housing_stress_verdict: str                          # "Tolerable" | "Crítica" | "Parasitaria"
    destructive_debt_index: float                        # IDD: % deuda basura vs tolerable
    destructive_debt_items: List[str]                   # "Tarjeta crédito €X", "Coche €X", etc
    months_to_zero_debt: int                            # Meses exactos usando avalancha
    debt_freedom_date: str                              # "14 de marzo de 2028"
    monthly_freed_cash: float                           # Cash liberado post-zero debt
    narrative: str                                      # Narrativa cruda de asfixia


@dataclass
class InvestmentAnalysis:
    """Espejo del Capital Inerte — radiografía del analfabetismo inversor"""
    invisible_inflation_tax_annual: float               # € perdidos por dinero parado
    scenario_a_bank_10y: float                          # Valor en 10 años si queda en banco
    scenario_b_indexed_10y: float                       # Valor en 10 años si se invierte (7% CAGR)
    scenario_gap_10y: float                             # Diferencia = coste del miedo
    investor_profile: str                               # "Conservador" | "Moderado" | "Decidido"
    investor_psych_tolerance: float                     # 0-100%: tolerancia volatilidad real
    recommended_strategy: str                           # "Letras + monetaria" vs "Fondos indexados" vs "Acciones"
    narrative_invisible_tax: str                        # "Has perdido X € este año a inflación"
    narrative_future_cost: str                          # "Diferencia = matrícula universidad o 20 años más trabajando"


@dataclass
class LifestyleAnalysis:
    """Auditoría del Lujo Miserable — donde la riqueza se convierte en pobreza de tiempo"""
    temporal_wealth_score: float                        # 0-100%: ratio tiempo vida vs ingresos
    hours_per_year_with_family: int                    # Horas reales con familia vs deseadas
    temporal_poverty_verdict: str                       # "Pobreza de Agenda" o "Equilibrio"
    hedonic_treadmill_status: str                       # "Atrapado" | "Estable" | "Mejorand"
    lifestyle_inflation_pct: float                     # % aumento gasto sin aumento felicidad
    status_dependent_spending_pct: float               # % presupuesto por validación social
    status_items: List[str]                            # "Coche €X", "Colegio privado €X", etc
    narrative_temporal: str                            # "Intercambias años de energía máxima..."
    narrative_hedonic: str                             # "Has caído en la cinta de correr..."
    narrative_status: str                              # "Compras cosas que no necesitas..."


@dataclass
class ImmunityScore:
    """Shield Score — resistencia del ecosistema familiar ante eventos catastróficos"""
    score_0_100: float                                 # Score final 0-100%
    category: str                                      # "Vulnerable" | "Resistente" | "Inmune/Antifrágil"
    resilience_months: int                             # Meses que aguanta sin cambios
    crisis_capacity: str                               # "Colapsa en 60d" | "Aguanta con sacrificio" | "Crisis = oportunidad"
    immunity_pillars: Dict[str, float]                # {debt: X%, investments: Y%, lifestyle: Z%}
    narrative: str                                     # "Una mala racha de 60 días..."


# ============ DEBT ANALYSIS ============

class DebtAnalyzer:
    """Termómetro de Presión Financiera — auditoría de toxicidad del apalancamiento"""

    @staticmethod
    def analyze(
        current_state: CurrentState,
        coi: COICalculation,
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int]
    ) -> DebtAnalysis:
        """
        Calcula TAI (Tasa de Asfixia Inmobiliaria) e IDD (Índice de Deuda Destructiva).
        """

        # Estimación de hipoteca % (preguntas Q151-Q175 sobre vivienda)
        housing_q_a = sum([user_a_answers.get(f"q{i}", 3) for i in range(151, 176)]) / 25
        housing_q_b = sum([user_b_answers.get(f"q{i}", 3) for i in range(151, 176)]) / 25
        estimated_housing_cost_pct = max(20, 45 - (housing_q_a + housing_q_b) / 2 * 5)

        # TAI: hipoteca + mantenimiento + seguros
        tai = estimated_housing_cost_pct + 3  # +3% mantenimiento/seguros

        if tai > 35:
            housing_stress_verdict = "Parasitaria"
        elif tai > 30:
            housing_stress_verdict = "Crítica"
        else:
            housing_stress_verdict = "Tolerable"

        # IDD: deuda basura (tarjetas + financiación + compras a plazo)
        destructive_debt_pct = max(0, (5 - housing_q_a) * 10 + (5 - housing_q_b) * 10)
        destructive_debt_items = [
            f"Tarjetas de crédito: ~€{destructive_debt_pct * 50:.0f}",
            f"Financiación vehículo: ~€{destructive_debt_pct * 30:.0f}",
            f"Compras a plazo: ~€{destructive_debt_pct * 20:.0f}"
        ]

        # Simulador "Libérate de Cadenas" (método avalancha)
        monthly_surplus = coi.vampire_expenses_annual / 12
        total_destructive_debt = destructive_debt_pct * 100  # Estimación
        months_to_zero = max(1, int(total_destructive_debt / monthly_surplus)) if monthly_surplus > 0 else 36

        from datetime import datetime, timedelta
        today = datetime.utcnow()
        zero_debt_date = today + timedelta(days=months_to_zero * 30)
        debt_freedom_date = zero_debt_date.strftime("%d de %B de %Y").replace("_", " ")

        monthly_freed_cash = (destructive_debt_pct * 100) / months_to_zero if months_to_zero > 0 else 0

        narrative = (
            f"Tu Tasa de Asfixia Inmobiliaria es {tai:.1f}% (categoría: {housing_stress_verdict}). "
            f"Tienes ~€{destructive_debt_pct * 100:.0f} en deuda destructiva. "
            f"Si aplicas el método avalancha hoy, el {debt_freedom_date} habrás eliminado el 100% de la deuda, "
            f"liberando €{monthly_freed_cash:.0f}/mes para tu jubilación."
        )

        return DebtAnalysis(
            housing_stress_rate=tai,
            housing_stress_verdict=housing_stress_verdict,
            destructive_debt_index=destructive_debt_pct,
            destructive_debt_items=destructive_debt_items,
            months_to_zero_debt=months_to_zero,
            debt_freedom_date=debt_freedom_date,
            monthly_freed_cash=monthly_freed_cash,
            narrative=narrative
        )


# ============ INVESTMENT ANALYSIS ============

class InvestmentAnalyzer:
    """Espejo del Capital Inerte — radiografía del analfabetismo inversor"""

    @staticmethod
    def analyze(
        current_state: CurrentState,
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int]
    ) -> InvestmentAnalysis:
        """
        Calcula Impuesto Invisible, Fórmula del Salto, Test de Compatibilidad Inversor.
        """

        # Dinero parado (estimado de Q251-Q300)
        assets_q = (
            sum([user_a_answers.get(f"q{i}", 2) for i in range(251, 301)]) / 50 +
            sum([user_b_answers.get(f"q{i}", 2) for i in range(251, 301)]) / 50
        ) / 2
        estimated_cash_idle = max(10000, (assets_q - 2) * 5000)

        # Impuesto Invisible: inflación 3% anual
        invisible_inflation_tax = estimated_cash_idle * 0.03

        # Escenarios a 10 años
        scenario_a_10y = estimated_cash_idle * (1 - 0.03 * 10)  # Dinero perdiendo valor
        scenario_b_10y = estimated_cash_idle * (1.07 ** 10)      # Fondos indexados 7% CAGR
        scenario_gap = scenario_b_10y - scenario_a_10y

        # Test de Perfil Inversor (Dimensión V, stress)
        stress_q = (
            sum([user_a_answers.get(f"q{i}", 3) for i in range(401, 451)]) / 50 +
            sum([user_b_answers.get(f"q{i}", 3) for i in range(401, 451)]) / 50
        ) / 2

        if stress_q < 2.5:
            investor_profile = "Conservador"
            tolerance = 30
            recommended = "Letras del Tesoro + Cuentas Monetarias de Alta Rentabilidad"
        elif stress_q < 3.5:
            investor_profile = "Moderado"
            tolerance = 60
            recommended = "Mix: 60% Renta Fija + 40% Fondos Indexados Diversificados"
        else:
            investor_profile = "Decidido"
            tolerance = 85
            recommended = "Fondos Indexados Automatizados (80% acciones + 20% renta fija)"

        narrative_invisible_tax = (
            f"Mantener esos €{estimated_cash_idle:,.0f} 'seguros' en tu cuenta corriente "
            f"te ha costado exactamente €{invisible_inflation_tax:,.0f} este año en pérdida "
            f"de poder adquisitivo. Tu miedo a invertir no te está protegiendo; está subvencionando "
            f"silenciosamente al banco."
        )

        narrative_future_cost = (
            f"En 10 años: Escenario A (banco) = €{scenario_a_10y:,.0f}. "
            f"Escenario B (fondos 7%) = €{scenario_b_10y:,.0f}. "
            f"La diferencia es €{scenario_gap:,.0f} — eso es la matrícula de la universidad "
            f"de tu hijo pagada por el interés compuesto, o pagada con sudor a los 60 años."
        )

        return InvestmentAnalysis(
            invisible_inflation_tax_annual=invisible_inflation_tax,
            scenario_a_bank_10y=scenario_a_10y,
            scenario_b_indexed_10y=scenario_b_10y,
            scenario_gap_10y=scenario_gap,
            investor_profile=investor_profile,
            investor_psych_tolerance=tolerance,
            recommended_strategy=recommended,
            narrative_invisible_tax=narrative_invisible_tax,
            narrative_future_cost=narrative_future_cost
        )


# ============ LIFESTYLE ANALYSIS ============

class LifestyleAnalyzer:
    """Auditoría del Lujo Miserable — donde riqueza se convierte en pobreza de tiempo"""

    @staticmethod
    def analyze(
        current_state: CurrentState,
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int],
        friction_map: FrictionMap
    ) -> LifestyleAnalysis:
        """
        Calcula Riqueza Temporal, Hedonic Treadmill, Semáforo Dependencia Estatus.
        """

        # Riqueza Temporal: coste hora vida vs tiempo familia
        avg_hourly_income = (sum(user_a_answers.values()) + sum(user_b_answers.values())) / 2 / 40
        annual_work_hours = current_state.weekly_household_hours * 52
        temporal_wealth = max(1, 100 - (annual_work_hours / 52 * 10))

        hours_with_family = max(10, 52 * 7 * (1 - current_state.weekly_household_hours / 100))
        if hours_with_family < 400:
            temporal_verdict = "Pobreza de Agenda"
        else:
            temporal_verdict = "Equilibrio"

        # Hedonic Treadmill: comparar ingresos hace 3 años vs ahora
        income_q = (
            sum([user_a_answers.get(f"q{i}", 3) for i in range(101, 151)]) / 50 +
            sum([user_b_answers.get(f"q{i}", 3) for i in range(101, 151)]) / 50
        ) / 2
        # Si ingresos altos pero estrés igual: hedonic treadmill
        if income_q > 4 and current_state.stress_level_1_5 > 3.5:
            hedonic_status = "Atrapado"
            lifestyle_inflation = 40
        else:
            hedonic_status = "Estable"
            lifestyle_inflation = 15

        # Semáforo Dependencia Estatus: Q476-Q500 (dimensión V)
        status_q = sum([user_a_answers.get(f"q{i}", 3) for i in range(476, 501)]) / 25 + \
                   sum([user_b_answers.get(f"q{i}", 3) for i in range(476, 501)]) / 25 / 2
        status_dependent_pct = max(0, (5 - status_q) * 3)

        status_items = [
            f"Coche premium/actualización anual: €{status_dependent_pct * 400:.0f}",
            f"Colegio privado/actividades: €{status_dependent_pct * 300:.0f}",
            f"Viajes/ocio aspiracional: €{status_dependent_pct * 200:.0f}",
            f"Restaurantes/eventos sociales: €{status_dependent_pct * 150:.0f}"
        ]

        narrative_temporal = (
            f"Estás intercambiando tus años de máxima energía biológica "
            f"a cambio de un estilo de vida que no tienes tiempo de disfrutar. "
            f"Tienes un hogar del Top 5% en ingresos, pero tu tiempo libre "
            f"es equivalente al del percentil más bajo. Sufres de '{temporal_verdict}'."
        )

        narrative_hedonic = (
            f"Has caído en la trampa de la cinta de correr hedónica. "
            f"Corres más rápido (trabajas más), ganas más, pero sigues exactamente "
            f"en el mismo lugar de estrés financiero que hace 3 años."
        )

        narrative_status = (
            f"Un {status_dependent_pct:.0f}% de tu presupuesto está destinado a validar "
            f"tu estatus frente a tu círculo social. Estás comprando cosas que no necesitas, "
            f"con dinero que te cuesta salud, para impresionar a gente que no te importa."
        )

        return LifestyleAnalysis(
            temporal_wealth_score=temporal_wealth,
            hours_per_year_with_family=int(hours_with_family),
            temporal_poverty_verdict=temporal_verdict,
            hedonic_treadmill_status=hedonic_status,
            lifestyle_inflation_pct=lifestyle_inflation,
            status_dependent_spending_pct=status_dependent_pct,
            status_items=status_items,
            narrative_temporal=narrative_temporal,
            narrative_hedonic=narrative_hedonic,
            narrative_status=narrative_status
        )


# ============ IMMUNITY SCORE (SHIELD SCORE) ============

class ImmunityScoreCalculator:
    """Shield Score — resistencia del hogar ante eventos catastróficos"""

    @staticmethod
    def calculate(
        debt_analysis: DebtAnalysis,
        investment_analysis: InvestmentAnalysis,
        lifestyle_analysis: LifestyleAnalysis,
        current_state: CurrentState
    ) -> ImmunityScore:
        """
        Calcula el Shield Score unificado (0-100%) que mide resistencia familiar.

        Pilares:
        - Debt Pillar: 100 - (TAI * 2) - (IDD * 1.5)
        - Investment Pillar: scenario_b_gap / scenario_a * 100
        - Lifestyle Pillar: temporal_wealth_score - status_dependent_pct * 2
        """

        # Pilar Deuda
        debt_pillar = max(0, 100 - (debt_analysis.housing_stress_rate * 2) - (debt_analysis.destructive_debt_index * 1.5))

        # Pilar Inversión
        if investment_analysis.scenario_gap_10y > 0:
            investment_pillar = min(100, (investment_analysis.scenario_gap_10y / investment_analysis.scenario_a_bank_10y) * 100)
        else:
            investment_pillar = 30

        # Pilar Lifestyle
        lifestyle_pillar = max(0, lifestyle_analysis.temporal_wealth_score - (lifestyle_analysis.status_dependent_spending_pct * 2))

        # Shield Score ponderado
        shield_score = (debt_pillar * 0.35) + (investment_pillar * 0.35) + (lifestyle_pillar * 0.30)

        if shield_score < 30:
            category = "Vulnerable"
            resilience = 2
            crisis_capacity = "Colapsa en 60 días"
        elif shield_score < 70:
            category = "Resistente"
            resilience = 6
            crisis_capacity = "Aguanta el golpe, pero a costa de sacrificar salud mental"
        else:
            category = "Inmune / Antifrágil"
            resilience = 24
            crisis_capacity = "Las crisis externas lo hacen más fuerte"

        immunity_pillars = {
            "debt_health": debt_pillar,
            "investment_readiness": investment_pillar,
            "lifestyle_sustainability": lifestyle_pillar
        }

        narrative = (
            f"Tu Shield Score es {shield_score:.0f}% ({category}). "
            f"Una mala racha laboral de {resilience} meses {'destruye tu hogar' if resilience < 3 else 'requiere sacrificios' if resilience < 12 else 'se convierte en oportunidad'}. "
            f"{'Necesitas acción inmediata en deudas y estilo de vida.' if resilience < 3 else 'Tienes margen, pero explota tu vulnerabilidad.' if resilience < 12 else 'Tu estructura está blindada.'}"
        )

        return ImmunityScore(
            score_0_100=shield_score,
            category=category,
            resilience_months=resilience,
            crisis_capacity=crisis_capacity,
            immunity_pillars=immunity_pillars,
            narrative=narrative
        )


# ============ THE 10% MULTIPLIER — EFECTO TIJERA EXPONENCIAL ============

@dataclass
class TenPercentScenario:
    """El Efecto Tijera: cómo un 10% simétrico duplica la capacidad de ahorro"""
    current_monthly_income: float                       # Ingresos actuales declarados
    current_monthly_expenses: float                     # Gastos actuales declarados
    current_savings_capacity: float                    # Capacidad ahorro actual (ingresos - gastos)

    income_after_10pct_increase: float                 # Ingresos + 10%
    expenses_after_10pct_cut: float                    # Gastos - 10%
    new_savings_capacity: float                        # Nueva capacidad ahorro (ingresos_new - gastos_new)

    savings_increase_percentage: float                 # % de aumento real en ahorro (120%+)
    effort_reduction_index: float                      # IRE: Índice de Retorno del Esfuerzo (0-100%)

    current_investment_return: float                   # Rentabilidad actual (2-4% típico)
    target_investment_return: float                    # Target: 10% con asignación correcta

    compound_wealth_10y_current: float                 # Patrimonio en 10 años sin cambios
    compound_wealth_10y_with_10pct: float             # Patrimonio en 10 años aplicando regla
    wealth_acceleration_months: int                   # Meses que acelera la riqueza

    narrative_impact: str                              # "Efecto Tijera duplica tu velocidad..."
    tactical_action_10days: str                        # "Reto de los 4 Dieces: comienza hoy"
    psychological_barrier_broken: bool                 # ¿Supera mentalidad de "imposible"?


class TheTenPercentMultiplier:
    """Módulo de Aceleración de Riqueza — La Regla Simétrica del 10%"""

    @staticmethod
    def calculate_ten_percent_effect(
        current_state: CurrentState,
        investment_analysis: InvestmentAnalysis,
        current_answers: Dict[str, int]
    ) -> TenPercentScenario:
        """
        Calcula el efecto exponencial de aplicar la regla del 10% SIMÉTRICA.
        No es un aumento simple; es el Efecto Tijera (ingresos ↑ + gastos ↓ = explosión ahorro).
        """

        # ============ EXTRAE LOS NÚMEROS REALES DEL USUARIO ============

        monthly_income = current_state.monthly_expenses_pct * 10  # Estimado desde gastos/ingresos
        monthly_expenses = current_state.monthly_expenses_pct

        # Capacidad de ahorro actual
        current_savings = monthly_income - monthly_expenses

        # ============ ESCENARIO DEL 10% SIMÉTRICO ============

        # Ingreso aumenta 10%: método "Monetizar Talento Infrautilizado"
        income_post_10pct = monthly_income * 1.10

        # Gastos bajan 10%: "Optimización Quirúrgica en Vampiros"
        expenses_post_10pct = monthly_expenses * 0.90

        # La magia: nueva capacidad de ahorro
        new_savings_capacity = income_post_10pct - expenses_post_10pct

        # % real de aumento en ahorro
        if current_savings > 0:
            savings_increase_pct = ((new_savings_capacity - current_savings) / current_savings) * 100
        else:
            savings_increase_pct = 100

        # ============ IRE: ÍNDICE DE RETORNO DEL ESFUERZO ============
        # ¿Cuánto esfuerzo extra cuesta lograr el mismo aumento por la vía tradicional?
        # (Trabajo más horas / pedir ascenso)

        effort_traditional = ((new_savings_capacity - current_savings) / monthly_income) * 100
        effort_ten_percent = 10  # Solo necesitas un 10% de cambio en dos vectores
        effort_reduction_index = max(0, 100 - (effort_traditional - effort_ten_percent))

        # ============ RENTABILIDAD DE INVERSIÓN ============

        current_return = investment_analysis.investor_psych_tolerance * 0.1  # 3-8.5% típico
        target_return = 0.10  # 10% con asignación correcta (fondos indexados)

        # ============ PROYECCIÓN A 10 AÑOS (COMPUESTO) ============

        # Escenario actual (sin cambios)
        annual_savings_current = current_savings * 12
        monthly_compound_current = annual_savings_current * (1 + current_return)
        wealth_10y_current = sum([
            annual_savings_current * ((1 + current_return) ** year)
            for year in range(1, 11)
        ])

        # Escenario con regla 10%
        annual_savings_new = new_savings_capacity * 12
        wealth_10y_with_10pct = sum([
            annual_savings_new * ((1 + target_return) ** year)
            for year in range(1, 11)
        ])

        # ¿Cuántos meses de ahorro actual = la aceleración?
        wealth_gap = wealth_10y_with_10pct - wealth_10y_current
        months_accelerated = int((wealth_gap / annual_savings_current) / 12) if annual_savings_current > 0 else 0

        # ============ NARRATIVAS DINÁMICAS (IA GENERADA) ============

        narrative_impact = (
            f"Hacer un micro-ajuste del 10% en tu estructura financiera NO requiere sacrificios espartanos. "
            f"Sin embargo, debido al **Efecto Tijera**, tu capacidad de ahorro real no va a subir un 10%: "
            f"va a aumentar un **{savings_increase_pct:.0f}%**.\n\n"
            f"Cada mes en el nuevo sistema equivale a {new_savings_capacity / current_savings:.1f}x meses del sistema actual. "
            f"Has reducido a la mitad el tiempo necesario para construir el escudo financiero de tu familia.\n\n"
            f"Para conseguir estos €{new_savings_capacity - current_savings:.0f} extra mensuales con tu estructura actual, "
            f"tendrías que trabajar un {effort_traditional:.0f}% más de horas o pedir un ascenso mañana mismo. "
            f"Con la regla simétrica del 10%, el esfuerzo requerido es un {effort_reduction_index:.0f}% menor."
        )

        tactical_action = (
            f"**EL RETO DE LOS 4 DIECES** (10 días de prueba piloto)\n\n"
            f"Día 1-2: Audita tu cesta de la compra. Identifica el 10% de desperdicio (marcas premium innecesarias, duplicados).\n"
            f"Día 3-5: Automatiza el pre-ahorro: el día que recibas nómina, transfiere €{(new_savings_capacity * 0.10):.0f} a cuenta aparte.\n"
            f"Día 6-8: Identifica oportunidad +10% ingresos (freelance, negocio secundario, aumento pendiente).\n"
            f"Día 9-10: Rebalancea inversiones hacia cartera 10% (60% acciones indexadas + 40% renta fija defensiva).\n\n"
            f"Resultado esperado: Después de 10 días, habrás generado €{new_savings_capacity - current_savings:.0f}/mes de nuevo potencial."
        )

        psychological_barrier = savings_increase_pct > 50  # Si ahorro aumenta >50%, mentalidad cambia

        return TenPercentScenario(
            current_monthly_income=monthly_income,
            current_monthly_expenses=monthly_expenses,
            current_savings_capacity=current_savings,
            income_after_10pct_increase=income_post_10pct,
            expenses_after_10pct_cut=expenses_post_10pct,
            new_savings_capacity=new_savings_capacity,
            savings_increase_percentage=savings_increase_pct,
            effort_reduction_index=effort_reduction_index,
            current_investment_return=current_return,
            target_investment_return=target_return,
            compound_wealth_10y_current=wealth_10y_current,
            compound_wealth_10y_with_10pct=wealth_10y_with_10pct,
            wealth_acceleration_months=months_accelerated,
            narrative_impact=narrative_impact,
            tactical_action_10days=tactical_action,
            psychological_barrier_broken=psychological_barrier
        )


# ============ ULTRA-PREMIUM: INGRESOS MÚLTIPLES + PSICOLOGÍA PROFUNDA ============

@dataclass
class FinancialRunway:
    """Cronómetro de "Esperanza de Vida Financiera" — días/horas hasta quiebra total"""
    liquid_assets_total: float                         # Patrimonio líquido total (€)
    daily_cost_of_living: float                        # Coste diario real de vida (€/día)
    runway_days: int                                   # Días totales de solvencia
    runway_hours: int                                  # Horas adicionales (0-24)
    runway_minutes: int                                # Minutos adicionales (0-60)

    cost_per_unnecessary_expense_50: float             # "€50 extra = X horas de oxígeno"
    narrative_desperation_clock: str                   # "Te quedan 412 días, 6h 12min"
    psychological_impact: str                          # "Este es tu tiempo de respiro real"


@dataclass
class LifeEventImpact:
    """Impacto financiero de eventos vitales inevitables (educación, dependencia, sándwich)"""
    event_type: str                                    # "Educación hijos" / "Dependencia padres" / "Sándwich"
    timeline_years: int                                # En cuántos años ocurre
    estimated_annual_cost: float                       # Coste anual medio de mercado
    impact_on_savings_capacity_pct: float             # % de reducción en ahorro
    probability_occurrence: float                      # 0-100% probabilidad estadística
    warning_narrative: str                             # "A partir de 2029, entra zona de riesgo..."


@dataclass
class MoneyArchetype:
    """Arqueología psico-financiera — Arquetipos de relación con dinero (Dr. Brad Klontz)"""
    user_a_archetype: str                             # "Evasor" / "Adorador" / "Buscador Status" / "Guardián"
    user_b_archetype: str
    archetype_descriptions: Dict[str, str]            # Explicación de cada arquetipo

    conflict_score: float                             # 0-100%: nivel de fricción de pareja por dinero
    conflict_resolution: str                          # "Presupuesto de Ocio Ciego" u otra solución
    friction_narrative: str                           # "El 70% de discusiones son por arquetipos..."


@dataclass
class LegacyHabitIndex:
    """Índice de "Herencia de Hábitos" — cómo patrones financieros afectan a los hijos"""
    parent_financial_anxiety_score: float             # 0-100% nivel de estrés con dinero
    children_replication_probability: float           # % probabilidad de replicar patrones
    legacy_health_index: float                        # 0-100% "Salud de Legado"

    current_financial_education_at_home: float       # Qué tan bien educados financieramente
    trauma_pattern_description: str                   # "Miedo a invertir, desorden gastos..."
    children_future_impact: str                       # Narrativa de cómo afectará a los hijos


@dataclass
class PremiumUpsellTrigger:
    """Pregunta 500 como hook psicológico para venta high-ticket premium"""
    user_willingness_to_pay: bool                     # ¿Sí a 3h/mes con mentor?
    estimated_recovery_potential: float               # Cálculo de COI (€ a recuperar)
    offer_message: str                                # Mensaje personalizado de oferta
    high_ticket_offer_cta: str                        # Call-to-action para sesión 500€+


# ============ CALCULADORES ULTRA-PREMIUM ============

class FinancialRunwayCalculator:
    """Tablero de coche antiguo: tiempo hasta quiebra en días/horas/minutos"""

    @staticmethod
    def calculate(
        liquid_assets: float,
        monthly_expenses: float,
        user_answers: Dict[str, int]
    ) -> FinancialRunway:
        """
        Si MAÑANA cortaras todos tus ingresos, ¿cuánto tiempo sobrevives?
        No en meses (como piensa la gente), sino en días, horas y minutos reales.
        """

        daily_cost = monthly_expenses / 30.0
        total_days = int(liquid_assets / daily_cost) if daily_cost > 0 else 0

        # Desglose: días + horas + minutos
        remaining_after_days = liquid_assets - (int(total_days) * daily_cost)
        hours = int((remaining_after_days / daily_cost) * 24)
        remaining_after_hours = remaining_after_days - (hours * daily_cost / 24)
        minutes = int((remaining_after_hours / daily_cost) * 24 * 60)

        # Psicología: ¿cuánto tiempo ganas si eliminas €50 innecesarios?
        cost_per_50_euros = (50 / daily_cost)  # Horas adicionales

        narrative = (
            f"Si hoy a las 09:00 AM cortaras por completo tus ingresos, tu hogar tiene exactamente "
            f"{total_days} días, {hours} horas y {minutes} minutos de vida financiera antes de la quiebra total, "
            f"manteniendo tu estilo de vida actual.\n\n"
            f"Cada gasto innecesario de €50 que elimines hoy le añade {cost_per_50_euros:.1f} horas de oxígeno y paz real."
        )

        return FinancialRunway(
            liquid_assets_total=liquid_assets,
            daily_cost_of_living=daily_cost,
            runway_days=total_days,
            runway_hours=hours,
            runway_minutes=minutes,
            cost_per_unnecessary_expense_50=cost_per_50_euros,
            narrative_desperation_clock=f"{total_days} días, {hours}h {minutes}min",
            psychological_impact=narrative
        )


class LifeEventSimulator:
    """Test de estrés para eventos vitales: educación, dependencia, "sándwich" """

    @staticmethod
    def simulate(
        current_state: CurrentState,
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int]
    ) -> List[LifeEventImpact]:
        """
        Simulación de ciclo de vida: qué eventos inevitables afectarán el flujo de caja.
        """

        impacts = []

        # Evento 1: EDUCACIÓN HIJOS (si tienen)
        has_children = (user_a_answers.get("q276", 2) + user_b_answers.get("q276", 2)) / 2 > 2.5
        if has_children:
            # Coste promedio educación España: +3-5% anual inflación educativa
            annual_cost = 6000  # Estimado: actividades, tecnología, extraescolares
            timeline = 8  # Próximos 8 años
            impact_on_savings = (annual_cost / (current_state.monthly_expenses_pct * 12)) * 100

            impacts.append(LifeEventImpact(
                event_type="Educación Hijos + Inflación Educativa",
                timeline_years=timeline,
                estimated_annual_cost=annual_cost,
                impact_on_savings_capacity_pct=min(impact_on_savings, 50),
                probability_occurrence=100,
                warning_narrative=(
                    f"A partir de {2026 + timeline}, el coste de educación y actividades de tus hijos "
                    f"consumirá {impact_on_savings:.1f}% adicional de tu excedente. "
                    f"Si no creas hoy el fondo indexado, licuarás tu ahorro futuro."
                )
            ))

        # Evento 2: DEPENDENCIA PADRES (si ambos > 70 años)
        parent_age_threshold = (user_a_answers.get("q301", 2) + user_b_answers.get("q301", 2)) / 2
        if parent_age_threshold > 3.5:  # Indicador de "padres mayores"
            annual_cost = 18000  # Coste medio dependencia España
            timeline = 3
            impact_on_savings = (annual_cost / (current_state.monthly_expenses_pct * 12)) * 100

            impacts.append(LifeEventImpact(
                event_type="Síndrome del Sándwich + Cuidado de Dependientes",
                timeline_years=timeline,
                estimated_annual_cost=annual_cost,
                impact_on_savings_capacity_pct=min(impact_on_savings, 60),
                probability_occurrence=75,
                warning_narrative=(
                    f"A partir de 2029, tu hogar entra en la zona estadística de carga de dependencia. "
                    f"Si no optimizas tus ingresos un 10% ahora, este evento vital licuará por completo tu excedente actual. "
                    f"Necesitas un plan B."
                )
            ))

        return impacts


class MoneyArchetypeAnalyzer:
    """Arqueología psico-financiera: asigna arquetipo a usuario y pareja, detecta fricción"""

    @staticmethod
    def analyze(
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int],
        friction_map: FrictionMap
    ) -> MoneyArchetype:
        """
        Los arquetipos de dinero de Dr. Brad Klontz: cómo la pareja choca financieramente.
        """

        # Preguntas que mapean arquetipos (dimensión V)
        # Evasor: evita mirar cuenta, ansiedad con dinero
        # Adorador: dinero = solución a todo, estatus
        # Buscador Estatus: gasta para validación social
        # Guardián: ahorra con miedo a escasez

        def assign_archetype(answers: Dict[str, int]) -> str:
            avoidance_score = sum([answers.get(f"q{i}", 2) for i in range(476, 486)]) / 10
            worship_score = sum([answers.get(f"q{i}", 2) for i in range(486, 496)]) / 10
            status_score = sum([answers.get(f"q{i}", 2) for i in range(496, 501)]) / 5

            if avoidance_score > 3.5:
                return "Evasor"
            elif worship_score > 3.5:
                return "Adorador"
            elif status_score > 3.5:
                return "Buscador de Estatus"
            else:
                return "Guardián"

        archetype_a = assign_archetype(user_a_answers)
        archetype_b = assign_archetype(user_b_answers)

        # Detectar fricción de pareja
        conflict_matrix = {
            ("Guardián", "Buscador de Estatus"): 85,
            ("Buscador de Estatus", "Guardián"): 85,
            ("Evasor", "Adorador"): 70,
            ("Adorador", "Evasor"): 70,
            ("Guardián", "Evasor"): 60,
            ("Evasor", "Guardián"): 60,
        }

        conflict_score = conflict_matrix.get((archetype_a, archetype_b), 25)

        descriptions = {
            "Evasor": "Evita mirar la cuenta bancaria por ansiedad. Actitud: 'Si no lo veo, no existe'.",
            "Adorador": "Cree que el dinero soluciona todos los problemas emocionales. Busca validación en la compra.",
            "Buscador de Estatus": "Gasta para impresionar. Su valor personal = lo que posee.",
            "Guardián": "Ahorra obsesivamente por miedo a la escasez. Experimenta ansiedad si no hay colchón."
        }

        if conflict_score > 70:
            resolution = (
                f"Vuestro conflicto NO es por falta de dinero, sino por colisión de arquetipos. "
                f"Un {archetype_a} que necesita seguridad choca con un {archetype_b} que busca validación. "
                f"Solución: Presupuesto de Ocio Ciego mensual (cantidad fija para gastar sin culpa)."
            )
        else:
            resolution = (
                f"Vuestra relación con el dinero es relativamente compatible. "
                f"Enfocad en la Regla del 10% y el plan de diversificación de ingresos."
            )

        narrative = (
            f"El {conflict_score:.0f}% de vuestras discusiones financieras no son sobre dinero, "
            f"sino sobre cómo interpretáis el dinero. {archetype_a} vs {archetype_b} = fricción inevitable. "
            f"Reconocerlo es el primer paso para convivir con ello."
        )

        return MoneyArchetype(
            user_a_archetype=archetype_a,
            user_b_archetype=archetype_b,
            archetype_descriptions=descriptions,
            conflict_score=conflict_score,
            conflict_resolution=resolution,
            friction_narrative=narrative
        )


class LegacyHabitIndexCalculator:
    """Índice de "Herencia de Hábitos" — cómo patrones financieros afectan a los hijos"""

    @staticmethod
    def calculate(
        current_state: CurrentState,
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int]
    ) -> LegacyHabitIndex:
        """
        La pregunta existencial: ¿qué legado financiero estamos dejando a los hijos?
        """

        # Ansiedad financiera parental (dimensión V)
        parental_anxiety = (
            (5 - user_a_answers.get("q451", 3)) +
            (5 - user_b_answers.get("q451", 3))
        ) / 2

        # Probabilidad de que los hijos repliquen: high stress parenting = high financial stress kids
        replication_probability = min(100, (parental_anxiety / 5) * 100)

        # Health index
        financial_education = (user_a_answers.get("q426", 2) + user_b_answers.get("q426", 2)) / 2
        legacy_health = max(0, 100 - replication_probability + (financial_education * 10))

        trauma_patterns = [
            "Miedo a invertir más allá del depósito tradicional",
            "Desorden crónico en gastos vampiro sin control",
            "Conversaciones sobre dinero = conflicto marital",
            "Normalización de deuda como estatus quo",
            "Escasez mental: 'Nunca hay suficiente'"
        ]

        current_pattern = trauma_patterns[int(parental_anxiety)] if parental_anxiety < 5 else "Multitrauma financiero"

        children_impact = (
            f"Tus hijos tienen un {replication_probability:.0f}% de probabilidad de replicar tus patrones de estrés "
            f"financiero en su vida adulta. El miedo a invertir o el desorden que ven hoy en la mesa del comedor "
            f"será su decisión financiera a los 30 años. Corregir tu estructura hoy NO es contabilidad personal: "
            f"es blindaje mental de la siguiente generación."
        )

        return LegacyHabitIndex(
            parent_financial_anxiety_score=parental_anxiety * 20,
            children_replication_probability=replication_probability,
            legacy_health_index=legacy_health,
            current_financial_education_at_home=financial_education * 20,
            trauma_pattern_description=current_pattern,
            children_future_impact=children_impact
        )


# ============ INCOME ECOSYSTEM ARCHITECT — DIVERSIFICACIÓN MULTICANAL ============

@dataclass
class IncomeRecommendation:
    """Una fuente de ingreso recomendada con viabilidad y potencial"""
    category: str                                      # A / B / C
    income_type: str                                   # Nombre de la fuente
    monthly_potential_low: float                       # Rango bajo €/mes
    monthly_potential_high: float                      # Rango alto €/mes
    effort_level: str                                  # "Nula" / "Baja" / "Media" / "Alta"
    time_required_monthly_hours: float                # Horas/mes para comenzar
    capital_required: float                           # € iniciales
    viability_score: float                            # 0-100% basado en perfil
    implementation_steps: List[str]                   # 3-5 pasos accionables
    risk_level: str                                   # "Bajo" / "Medio" / "Alto"
    synergy_with_current: str                         # Cómo se alinea con profesión actual


@dataclass
class DiversificationRiskIndex:
    """Índice de diversificación de ingresos — riesgo de concentración"""
    diversification_score: float                      # 0-100% (100 = perfectamente diversificado)
    current_concentration: str                        # "Mono" / "Dual" / "Multi"
    herfindahl_index: float                          # Métrica de concentración (0-1)
    recommended_sources_count: int                    # Cuántas fuentes ideales
    gap_to_resilience: float                         # % de mejora posible
    simulation_5_years: Dict[str, float]             # Proyección si se implementan recomendaciones


@dataclass
class FamilyIncomeTreeNode:
    """Nodo de árbol de ingresos familiares — trunk, ramas, follaje"""
    node_type: str                                    # "trunk" / "branch" / "leaf"
    income_source: str                                # "Nómina Javier" / "Honorarios" / etc.
    annual_amount: float                              # € anuales
    passivity_level: int                              # 1-5 (1=activo, 5=pasivo)
    color_code: str                                   # Color para visualizar #XXXXXX


@dataclass
class IncomeEcosystemAnalysis:
    """Análisis completo del ecosistema de ingresos + recomendaciones"""
    current_income_sources: List[str]                # Fuentes actuales
    recommendations: List[IncomeRecommendation]      # 6-9 opciones según viabilidad
    family_income_tree: List[FamilyIncomeTreeNode]   # Estructura visual
    diversification_index: DiversificationRiskIndex  # Métrica de riesgo
    implementation_roadmap: str                       # "Mes 1: hacer X. Mes 2: hacer Y..."
    narrative_income_strategy: str                    # Story de cómo convertir 1 ingreso en 3


class IncomeEcosystemArchitect:
    """Arquitecto de ecosistemas de ingresos — diseña estrategias multicanal sin esfuerzo"""

    @staticmethod
    def analyze(
        current_state: CurrentState,
        user_a_answers: Dict[str, int],
        user_b_answers: Dict[str, int],
        ten_percent_multiplier: TheTenPercentMultiplier = None
    ) -> IncomeEcosystemAnalysis:
        """
        Diseña un ecosistema de ingresos múltiples basado en:
        - Capital disponible (Dimensión II)
        - Tiempo/Carga mental (Dimensiones I & V)
        - Profesión actual + nicho expertise
        """

        # PASO 1: Extraer capital y tiempo disponibles
        capital_available = current_state.monthly_cash_buffer  # € con los que trabajar
        monthly_hours_available = max(0, 160 - (
            (5 - user_a_answers.get("q151", 3)) * 20 +  # Horas trabajo actual Javier
            (5 - user_b_answers.get("q151", 3)) * 20     # + Horas trabajo actual Bea
        )) / 2  # Promedio disponible

        # PASO 2: Viability Filter — ¿qué categorías funcionan?
        recommendations = []

        # CATEGORÍA A: Passive Income Liquids (CERO esfuerzo)
        # Mover dinero de tradicional a monetarias + reinversión automática
        if capital_available > 5000:  # Mínimo para monetarias
            recommendations.append(IncomeRecommendation(
                category="A",
                income_type="Cuentas Monetarias + Fondos Renta Fija Corto Plazo",
                monthly_potential_low=(capital_available * 0.045) / 12,  # 4.5% APY
                monthly_potential_high=(capital_available * 0.055) / 12,  # 5.5% APY
                effort_level="Nula",
                time_required_monthly_hours=0.25,  # Transfer online = 15 min
                capital_required=1000,
                viability_score=100,  # Siempre viable si hay capital
                implementation_steps=[
                    "Abrir cuenta en Openbank, Yadio o Cobee (5 min online)",
                    "Transferir €X de cuenta corriente (automático)",
                    "Activar reinversión automática de intereses",
                    "Revisar trim (5 min al trimestre)"
                ],
                risk_level="Bajo",
                synergy_with_current="Complementa perfectamente sin tocar profesión"
            ))

        # CATEGORÍA A: Dividend-Yielding ETFs (Semi-pasivo, bajo esfuerzo)
        if capital_available > 10000:
            recommendations.append(IncomeRecommendation(
                category="A",
                income_type="ETF Dividend Yielding (VYM, VYMI, AGGG)",
                monthly_potential_low=(capital_available * 0.035) / 12,  # 3.5% yield
                monthly_potential_high=(capital_available * 0.045) / 12,  # 4.5% yield
                effort_level="Nula",
                time_required_monthly_hours=0,
                capital_required=5000,
                viability_score=90,
                implementation_steps=[
                    "Abrir bróker online (Interactive Brokers, DEGIRO)",
                    "Comprar cartera de 3-5 ETF dividend",
                    "Activar reinversión automática (Dividend Reinvestment Plan)",
                    "Set & forget — revisar anual"
                ],
                risk_level="Bajo",
                synergy_with_current="Completamente pasivo; complementa dinero en banco"
            ))

        # CATEGORÍA B: Semi-Passive (Conocimiento monetizado)
        # Si tiene expertise profesional, empaquetarlo
        professional_expertise_level = (
            user_a_answers.get("q126", 2) + user_b_answers.get("q126", 2)
        ) / 2  # Autoestima de expertise

        if professional_expertise_level >= 3.5 and monthly_hours_available > 20:
            recommendations.append(IncomeRecommendation(
                category="B",
                income_type="Infoproductos + Plantillas Premium (Gumroad/Teachable)",
                monthly_potential_low=500,
                monthly_potential_high=3000,
                effort_level="Media (creación inicial)",
                time_required_monthly_hours=8,
                capital_required=0,
                viability_score=85 if professional_expertise_level > 4 else 65,
                implementation_steps=[
                    "Documentar tu metodología (10 horas)",
                    "Crear 2-3 templates/checklists premium",
                    "Subir a Gumroad con landing page simple",
                    "Promocionar en LinkedIn 1x/semana (esfuerzo mínimo)"
                ],
                risk_level="Bajo",
                synergy_with_current="Amplifica tu reputación profesional; genera 500-3k/mes pasivamente"
            ))

        # CATEGORÍA B: Mentoría/Consultoría Micro (si tiene experiencia)
        if user_a_answers.get("q476", 2) + user_b_answers.get("q476", 2) >= 5:
            recommendations.append(IncomeRecommendation(
                category="B",
                income_type="Sesiones de Mentoría 1-on-1 (Calendly + Stripe)",
                monthly_potential_low=800,
                monthly_potential_high=2500,
                effort_level="Media",
                time_required_monthly_hours=10,
                capital_required=100,  # Calendly + Stripe setup
                viability_score=80,
                implementation_steps=[
                    "Fijar tarifa por sesión (€99-150/h)",
                    "Activar Calendly con Stripe payment",
                    "Crear página de landing simple (Webflow/Carrd)",
                    "Buscar 4-6 mentorados/mes = €3.2-9k/mes"
                ],
                risk_level="Bajo",
                synergy_with_current="Apalanca expertise sin crear contenido masivo"
            ))

        # CATEGORÍA C: Wealth Optimization (Activos ocultos)
        # Si tiene propiedad segunda vivienda, vehículo, etc.
        has_second_property = user_a_answers.get("q266", 2) > 2.5
        has_vehicle = user_a_answers.get("q268", 2) > 2.5

        if has_second_property:
            recommendations.append(IncomeRecommendation(
                category="C",
                income_type="Alquiler Vacacional (Airbnb/Booking) — 2ª Vivienda",
                monthly_potential_low=600,
                monthly_potential_high=2000,
                effort_level="Baja",
                time_required_monthly_hours=5,
                capital_required=500,  # Fotos profesionales, limpieza inicial
                viability_score=90 if has_second_property else 0,
                implementation_steps=[
                    "Fotografías profesionales de la vivienda",
                    "Crear lista en Airbnb + Booking",
                    "Automatizar check-in (cerraduras inteligentes)",
                    "Contratar gestor de limpieza = €50-80/estancia"
                ],
                risk_level="Bajo",
                synergy_with_current="Monetiza activo infrautilizado; cash flow sin esfuerzo"
            ))

        if has_vehicle:
            recommendations.append(IncomeRecommendation(
                category="C",
                income_type="Vehículo en Sharing (Turo/Share Now/BlaBlaCar)",
                monthly_potential_low=400,
                monthly_potential_high=1200,
                effort_level="Nula",
                time_required_monthly_hours=0.5,
                capital_required=200,
                viability_score=75,
                implementation_steps=[
                    "Inscribir vehículo en Turo (30 min setup)",
                    "Establecer tarifa competitiva vs mercado local",
                    "Automatizar acceso remoto via app",
                    "Dejar funcionar; ganancias van a tu cuenta"
                ],
                risk_level="Medio",
                synergy_with_current="Activo que ya tienes genera cash sin tocar tu negocio"
            ))

        # PASO 3: Construir Family Income Tree (visualización)
        family_income_tree = []

        # Trunk
        family_income_tree.append(FamilyIncomeTreeNode(
            node_type="trunk",
            income_source=f"Ingresos Primarios (Profesión)",
            annual_amount=current_state.monthly_income * 12,
            passivity_level=1,
            color_code="#020203"  # Negro corporativo
        ))

        # Ramas (recomendaciones principales)
        for i, rec in enumerate(recommendations[:3]):  # Top 3 por viabilidad
            family_income_tree.append(FamilyIncomeTreeNode(
                node_type="branch",
                income_source=rec.income_type,
                annual_amount=(rec.monthly_potential_low + rec.monthly_potential_high) / 2 * 12,
                passivity_level=min(5, (5 - ord(rec.category) + ord('A')) + (1 if "Pasivo" in rec.income_type or rec.effort_level == "Nula" else 0)),
                color_code="#FDD731" if rec.passivity_level >= 4 else "#F4CB2E"
            ))

        # PASO 4: Calcular Diversification Risk Index (IDR)
        current_sources = [s for s in current_state.income_sources if s]
        num_current = max(1, len(current_sources))

        # Herfindahl-Hirschman Index: ∑(% de cada fuente)²
        herfindahl = 1.0 / num_current if num_current > 0 else 1.0

        # Diversification score: cuán cerca estamos del ideal (3-4 fuentes)
        ideal_sources = 4
        current_concentration = "Mono" if num_current == 1 else ("Dual" if num_current == 2 else "Multi")

        # Si aplicamos recomendaciones, mejora dramáticamente
        post_impl_sources = num_current + min(3, len([r for r in recommendations if r.viability_score >= 75]))
        post_impl_herfindahl = 1.0 / post_impl_sources

        diversification_score = (1 - (herfindahl / 1.0)) * 100  # Normalizar a 0-100%

        # Simulación 5 años
        base_annual = current_state.monthly_income * 12
        simulation = {
            "Year 1 Current": base_annual,
            "Year 1 With Recs": base_annual + sum([r.monthly_potential_low * 8 for r in recommendations[:2]]),  # 2 fuentes en año 1
            "Year 5 Current": base_annual,
            "Year 5 With Recs": (
                base_annual * 1.03 +  # Crecimiento base 3%
                sum([r.monthly_potential_high * 12 for r in recommendations[:3]])  # 3 fuentes a full potential
            )
        }

        diversification_index = DiversificationRiskIndex(
            diversification_score=max(25, min(100, diversification_score + (len(recommendations) * 15))),
            current_concentration=current_concentration,
            herfindahl_index=herfindahl,
            recommended_sources_count=ideal_sources,
            gap_to_resilience=(1 - (post_impl_herfindahl / herfindahl)) * 100 if herfindahl > 0 else 0,
            simulation_5_years=simulation
        )

        # PASO 5: Roadmap de implementación
        roadmap = (
            "**MES 1 — CIMIENTOS (Effort: 3 horas)**\n"
            f"1. Abrir cuenta en monetaria (Openbank): {recommendations[0].monthly_potential_low:.0f}€/mes automático\n"
            f"2. Transferir excedente mensual al día 1 de cada mes\n\n"
            "**MES 2-3 — RAMAS INICIALES (Effort: 10 horas)**\n"
            f"3. Configurar ETF dividend en bróker: {recommendations[1].monthly_potential_low if len(recommendations) > 1 else 100:.0f}€/mes\n"
            f"4. Documentar tu expertise en 1 checklist premium (Gumroad)\n\n"
            "**MES 4-6 — OPTIMIZACIÓN (Effort: 15 horas)**\n"
            f"5. Activar monetización de segundo activo (Airbnb/Turo si aplica)\n"
            f"6. Configurar landing page de mentoría; buscar 2 primeros mentorados\n\n"
            "**RESULTADO ESPERADO AÑO 1:**\n"
            f"- Ingresos pasivos: +€800-1200/mes (automatizado)\n"
            f"- Income diversification: {diversification_index.diversification_score:.0f}%\n"
            f"- Cash flow year 5: +€8,000-15,000/año sin más esfuerzo que hoy"
        )

        # PASO 6: Narrativa estratégica
        narrative = (
            f"Tu hogar tiene UN ingreso principal (profesión). "
            f"Eso es vulnerable. Un cambio laboral, un problema de salud, y todo colapsa. "
            f"Pero tienes {len(recommendations)} oportunidades de crear ingresos paralelos "
            f"sin necesidad de un segundo trabajo.\n\n"
            f"La diferencia: el primero toma 40 horas/semana de tu tiempo. "
            f"Estos {len(recommendations)} toman, combinados, menos de 20 horas iniciales de documentación y setup. "
            f"Luego: completamente pasivos.\n\n"
            f"En 5 años, si implementas esto, tu IDR (diversificación) pasa de {diversification_index.current_concentration} a Multi-channel. "
            f"Y tus ingresos anuales: de €{base_annual:,.0f} a €{simulation['Year 5 With Recs']:,.0f}. "
            f"No por más esfuerzo hoy. Por inteligencia diseño hoy."
        )

        return IncomeEcosystemAnalysis(
            current_income_sources=current_sources,
            recommendations=recommendations,
            family_income_tree=family_income_tree,
            diversification_index=diversification_index,
            implementation_roadmap=roadmap,
            narrative_income_strategy=narrative
        )


class PremiumUpsellOptimizer:
    """Pregunta 500 como psico-gatillo para venta high-ticket (consultoría 500€+)"""

    @staticmethod
    def generate_trigger(
        willing_to_work_with_mentor: bool,
        coi_calculation: COICalculation,
        legacy_index: LegacyHabitIndex
    ) -> PremiumUpsellTrigger:
        """
        Si respondió SÍ a "¿Dedicarías 3h/mes con mentor?", es candidato premium.
        """

        recovery_potential = coi_calculation.total_annual_loss

        offer_message = (
            f"✅ **Felicidades. Has demostrado compromiso.**\n\n"
            f"Tu diagnóstico demuestra un potencial de recuperación patrimonial de **€{recovery_potential:,.0f}**. "
            f"El software ha hecho el mapa, pero la disciplina la pones tú.\n\n"
            f"Como has respondido 500 preguntas y estás dispuesto a dedicar 3h/mes con un mentor, "
            f"tienes acceso prioritario a una sesión de validación de tu Hoja de Ruta."
        )

        cta = (
            f"[AGENDAR SESIÓN DE VALIDACIÓN EN VIVO]\n"
            f"Auditoría personalizada + Hoja de Ruta Blindada\n"
            f"Duración: 90 minutos | Inversión: €500\n"
            f"Resultado: Plan de acción ejecutable para los próximos 12 meses"
        )

        return PremiumUpsellTrigger(
            user_willingness_to_pay=willing_to_work_with_mentor,
            estimated_recovery_potential=recovery_potential,
            offer_message=offer_message,
            high_ticket_offer_cta=cta
        )


class FamilyAlignmentActGenerator:
    """Genera Acta de Alineación Estratégica — documento vinculante emocionalmente"""

    @staticmethod
    def generate(
        couple_id: str,
        user_a_name: str,
        user_b_name: str,
        leverage_point: LeveragePoint,
        archetype: ArchetypeProfile,
        ideal_state: IdealState,
        today_date: str
    ) -> FamilyAlignmentAct:
        """
        Crea un documento formal que convierte diagnóstico en promesa vinculante.
        """

        three_commitments = [
            f"Implementar plan de {leverage_point.action.lower()} en las próximas 2 semanas",
            f"Revisión conjunta de finanzas el primer lunes de cada mes (30 minutos)",
            f"Alcanzar fondo de emergencia de {ideal_state.emergency_buffer_months} meses en 6 meses"
        ]

        formal_statement = (
            f"Nosotros, {user_a_name} y {user_b_name}, habiendo realizado el análisis de diagnóstico "
            f"patrimonial y relacional integral a través de 'Espejo Fantasma', reconocemos nuestra situación actual "
            f"como familia de arquetipo '{archetype.name}'. "
            f"\n\nNos comprometemos públicamente con los tres objetivos estratégicos enumerados abajo, durante los próximos "
            f"6 meses, como primer paso hacia nuestro Estado Ideal de {ideal_state.family_quality_of_life_descriptor}. "
            f"\n\nEste acta constituye nuestra declaración de intención y nuestro protocolo de revisión semestral."
        )

        signature_lines = {
            "user_a_name": f"{user_a_name}: ________________________   Fecha: ________",
            "user_b_name": f"{user_b_name}: ________________________   Fecha: ________",
        }

        next_review_date = f"6 meses desde {today_date}"

        return FamilyAlignmentAct(
            family_name=f"{user_a_name} & {user_b_name}",
            assessment_date=today_date,
            three_key_commitments=three_commitments,
            commitment_period_months=6,
            signature_lines=signature_lines,
            witness_line="Javier Méndez, Adapta Family Office: ________________________",
            formal_statement=formal_statement,
            next_review_date=next_review_date
        )
