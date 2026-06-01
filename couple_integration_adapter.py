#!/usr/bin/env python3
"""
COUPLE INTEGRATION ADAPTER — FASE 2 Sprint 2
Orquestador que conecta couple_management.py (ORM) con friction_detection.py (23 módulos).
TOP 1% MUNDIAL — Sin intermediarios, sin abstracciones innecesarias.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import json

from couple_management import CoupleSession, CoupleAnswers, CoupleReport, CoupleService
from friction_detection import (
    ResponseValidator, FrictionCalculator, FrictionInsights, QuickWinsPlanner,
    COICalculator, ArchetypeDetector, FODACalculator, CurrentStateAnalyzer,
    DebtAnalyzer, InvestmentAnalyzer, LifestyleAnalyzer, ImmunityScoreCalculator,
    TheTenPercentMultiplier, FinancialRunwayCalculator, LifeEventSimulator,
    MoneyArchetypeAnalyzer, LegacyHabitIndexCalculator, PremiumUpsellOptimizer,
    IncomeEcosystemArchitect
)


class CoupleIntegrationAdapter:
    """Orquestador end-to-end: ORM → análisis 23 módulos → PDF + insights"""

    def __init__(self, db_session=None):
        self.db = db_session
        self.couple_service = CoupleService(db_session)

    def process_couple_answers(
        self,
        couple_id: str,
        user_a_answers: Dict[int, int],
        user_b_answers: Dict[int, int],
        generate_pdf: bool = True
    ) -> Dict:
        """
        Pipeline end-to-end:
        1. Validar respuestas
        2. Ejecutar 23 módulos diagnósticos
        3. Guardar en DB (CoupleReport)
        4. Generar PDF (async opcional)
        5. Retornar análisis + URLs
        """

        # PASO 1: Validación
        try:
            validated_a = ResponseValidator.validate_answers(user_a_answers)
            validated_b = ResponseValidator.validate_answers(user_b_answers)
        except ValueError as e:
            return {"error": f"Validation failed: {str(e)}", "status": 400}

        # PASO 2: Detectar hijos (q001) para activar Family Central Bank
        tiene_hijos_a = user_a_answers.get(1, 0) > 0  # q001
        tiene_hijos_b = user_b_answers.get(1, 0) > 0
        tiene_hijos = tiene_hijos_a or tiene_hijos_b

        # PASO 3: Ejecutar cascada de 23 módulos
        analysis_result = self._run_friction_analysis_cascade(
            user_a_answers, user_b_answers, tiene_hijos
        )

        # PASO 4: Guardar en DB
        couple_record = CoupleSession(
            id=couple_id or str(uuid.uuid4()),
            user_a_id=f"user_a_{couple_id}",
            user_b_id=f"user_b_{couple_id}",
            status="completed",
            tiene_hijos=tiene_hijos,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=72)  # 72h TTL GDPR
        )

        couple_answers_a = CoupleAnswers(
            couple_session_id=couple_id,
            user_id="user_a",
            answers=json.dumps(user_a_answers),
            created_at=datetime.utcnow()
        )

        couple_answers_b = CoupleAnswers(
            couple_session_id=couple_id,
            user_id="user_b",
            answers=json.dumps(user_b_answers),
            created_at=datetime.utcnow()
        )

        # Guardar análisis en CoupleReport
        couple_report = CoupleReport(
            couple_session_id=couple_id,
            friction_score=analysis_result.get("compatibility_score", 0),
            shield_score=analysis_result.get("shield_score", 0),
            runway_days=analysis_result.get("runway_days", 0),
            report_data=json.dumps(analysis_result),
            pdf_url=None,  # Se rellenará si se genera PDF
            created_at=datetime.utcnow()
        )

        if self.db:
            self.db.add(couple_record)
            self.db.add(couple_answers_a)
            self.db.add(couple_answers_b)
            self.db.add(couple_report)
            self.db.commit()

        # PASO 5: Generar PDF (async)
        pdf_url = None
        if generate_pdf:
            pdf_url = self._trigger_pdf_generation_async(couple_id, analysis_result)
            couple_report.pdf_url = pdf_url
            if self.db:
                self.db.commit()

        return {
            "couple_id": couple_id,
            "status": "success",
            "compatibility_score": analysis_result.get("compatibility_score"),
            "shield_score": analysis_result.get("shield_score"),
            "runway_days": analysis_result.get("runway_days"),
            "tiene_hijos": tiene_hijos,
            "high_ticket_trigger": analysis_result.get("high_ticket_trigger"),
            "pdf_url": pdf_url,
            "expires_at": (datetime.utcnow() + timedelta(hours=72)).isoformat()
        }

    def _run_friction_analysis_cascade(self, user_a: Dict, user_b: Dict, tiene_hijos: bool) -> Dict:
        """Ejecutar los 23 módulos en cascada. Retorna análisis consolidado."""

        # MÓDULO 1-5: Base
        friction_map = FrictionCalculator.calculate_friction(user_a, user_b)
        friction_insights = FrictionInsights.detect_contradictions(user_a, user_b, friction_map)
        current_state = CurrentStateAnalyzer.analyze(user_a, user_b)
        ideal_state = CurrentStateAnalyzer.ideal_state_for_profile(current_state)
        archetype = ArchetypeDetector.detect(user_a, user_b)

        # MÓDULO 6-10: Análisis
        foda = FODACalculator.calculate(friction_map, current_state, archetype)
        coi = COICalculator.estimate(current_state, friction_map)
        debt = DebtAnalyzer.analyze(current_state, coi, user_a, user_b)
        investment = InvestmentAnalyzer.analyze(current_state, user_a, user_b)
        lifestyle = LifestyleAnalyzer.analyze(current_state, user_a, user_b)

        # MÓDULO 11-17: Aceleración
        ten_percent = TheTenPercentMultiplier.calculate(current_state)
        immunity = ImmunityScoreCalculator.calculate(debt, investment, lifestyle)
        quick_wins = QuickWinsPlanner.generate_4week_plan(current_state, coi, friction_map)

        # MÓDULO 18-23: Ultra-Premium
        runway = FinancialRunwayCalculator.calculate(
            current_state.monthly_liquid_assets,
            current_state.monthly_expenses,
            user_a
        )
        life_events = LifeEventSimulator.simulate(current_state, user_a, user_b)
        archetypes = MoneyArchetypeAnalyzer.analyze(user_a, user_b, friction_map)
        legacy = LegacyHabitIndexCalculator.calculate(current_state, user_a, user_b)
        income_ecosystem = IncomeEcosystemArchitect.analyze(
            current_state, user_a, user_b, ten_percent
        )

        # High-ticket trigger (q500/q501)
        q500_a = user_a.get(500, 0)
        q500_b = user_b.get(500, 0)
        willing_to_mentor = (q500_a + q500_b) >= 50
        upsell = PremiumUpsellOptimizer.generate_trigger(
            willing_to_mentor, coi, legacy, q500_score=(q500_a + q500_b)
        )

        return {
            "compatibility_score": friction_map.compatibility_score,
            "friction_narrative": friction_insights.friction_narrative,
            "shield_score": immunity.shield_score,
            "runway_days": runway.runway_days,
            "runway_narrative": runway.narrative_desperation_clock,
            "legacy_index": legacy.legacy_health_index,
            "children_replication_prob": legacy.children_replication_probability if tiene_hijos else 0,
            "archetype_a": archetypes.user_a_archetype,
            "archetype_b": archetypes.user_b_archetype,
            "archetype_conflict": archetypes.conflict_score,
            "income_diversification": income_ecosystem.diversification_index.diversification_score,
            "high_ticket_trigger": willing_to_mentor,
            "upsell_message": upsell.offer_message,
            "monthly_savings_potential": ten_percent.savings_increase,
            "tiene_hijos": tiene_hijos,
            "coi_narrative": coi.narrative_summary if hasattr(coi, 'narrative_summary') else "",
            "quick_wins": quick_wins.wins_list if hasattr(quick_wins, 'wins_list') else []
        }

    def _trigger_pdf_generation_async(self, couple_id: str, analysis: Dict) -> Optional[str]:
        """
        Disparar PDF async (simulado aquí, en producción usaría Celery/async task).
        Retorna URL de descarga.
        """
        # En producción: queue async PDF generation con Celery
        # Por ahora: simular URL
        return f"https://espejo-fantasma.com/reports/{couple_id}/diagnostico.pdf"

    # ============= GAMIFICATION: PARTIAL SCORE CALCULATION (MECÁNICA 1) =============
    def calculate_partial_scores(self, answers_so_far: Dict[int, int]) -> Dict[int, float]:
        """
        Calcula scores parciales por dimensión (5 dimensiones, 100 preguntas cada una).
        Retorna un dict con score 0-100 para cada dimensión.
        """
        scores = {}
        for dimension in range(1, 6):
            start_q = (dimension - 1) * 100 + 1
            end_q = dimension * 100
            dimension_answers = {q: v for q, v in answers_so_far.items() if start_q <= q <= end_q}

            if dimension_answers:
                avg_score = sum(dimension_answers.values()) / len(dimension_answers)
                scores[dimension] = round((avg_score / 5) * 100)  # Normalize to 0-100
            else:
                scores[dimension] = 0

        return scores

    # ============= GAMIFICATION: PATTERN DETECTION (MECÁNICA 4) =============
    def detect_patterns(self, answers_a: Dict[int, int], answers_b: Dict[int, int], current_q: int) -> Optional[Dict]:
        """
        Detecta patrones psicológicos / síndromes a partir de respuestas.
        Retorna un dict con {icon, title, text} si hay patrón detectado en esta pregunta.
        """
        PATTERN_TRIGGERS = {
            75: self._detect_gilded_cage,
            150: self._detect_debt_trap,
            250: self._detect_couple_friction,
            350: self._detect_planning_urgency
        }

        if current_q in PATTERN_TRIGGERS:
            return PATTERN_TRIGGERS[current_q](answers_a, answers_b)

        return None

    def _detect_gilded_cage(self, answers_a: Dict, answers_b: Dict) -> Dict:
        """Síndrome: Jaula de Oro (ingresos altos, bajo ahorro, estrés alto)"""
        high_income_q = [45, 46, 47]  # Mock: preguntas de ingresos
        high_stress_q = [60, 61, 62]  # Mock: preguntas de estrés
        low_savings_q = [30, 31, 32]  # Mock: preguntas de ahorro

        high_income = sum(answers_a.get(q, 0) + answers_b.get(q, 0) for q in high_income_q) > 12
        high_stress = sum(answers_a.get(q, 0) + answers_b.get(q, 0) for q in high_stress_q) > 12
        low_savings = sum(answers_a.get(q, 0) + answers_b.get(q, 0) for q in low_savings_q) < 6

        if high_income and high_stress and low_savings:
            return {
                "icon": "💼",
                "title": "Síndrome de la Jaula de Oro",
                "text": "Ganas bien pero el dinero se te escapa. No te preocupes, en el siguiente bloque daremos soluciones."
            }
        return None

    def _detect_debt_trap(self, answers_a: Dict, answers_b: Dict) -> Dict:
        """Síndrome: Trampa de Deuda (alto endeudamiento sin inversión)"""
        debt_ratio = sum(answers_a.get(q, 0) + answers_b.get(q, 0) for q in [80, 81, 82]) / 6
        investment_zero = sum(answers_a.get(q, 0) + answers_b.get(q, 0) for q in [90, 91, 92]) < 3

        if debt_ratio > 3 and investment_zero:
            return {
                "icon": "⚠️",
                "title": "Trampa de Deuda",
                "text": "Detectamos endeudamiento sin inversión compensatoria. Es reversible."
            }
        return None

    def _detect_couple_friction(self, answers_a: Dict, answers_b: Dict) -> Dict:
        """Fricción: Desalineamiento en pareja"""
        disagreement_score = sum(abs(answers_a.get(q, 0) - answers_b.get(q, 0)) for q in range(1, 150))

        if disagreement_score > 50:
            return {
                "icon": "❤️",
                "title": "Fricción de Pareja Visible",
                "text": "No están alineados financieramente. Esto es el #1 predictor de conflicto. Pero es reparable."
            }
        return None

    def _detect_planning_urgency(self, answers_a: Dict, answers_b: Dict) -> Dict:
        """Urgencia: Falta de plan financiero conjunto"""
        planning_awareness = sum(answers_a.get(q, 0) + answers_b.get(q, 0) for q in [110, 111, 112]) / 6

        if planning_awareness < 2:
            return {
                "icon": "🎯",
                "title": "Urgencia de Planificación",
                "text": "No tienen un plan financiero conjunto. Sin uno, el futuro es volátil. Es hora de crear uno."
            }
        return None

    # ============= GAMIFICATION: FATIGUE DETECTION (MECÁNICA 5) =============
    @staticmethod
    def should_show_coffee_break(current_q: int, time_between_answers_ms: int) -> bool:
        """
        Detecta si el usuario está fatigado (preguntas lentas después de q250).
        Retorna True si debe mostrarse modal de café.
        """
        return current_q > 250 and time_between_answers_ms > 8000


# ENDPOINT WRAPPER — para FastAPI
def create_couple_endpoint_handler(db_session):
    """Factory para crear handler de endpoint POST /couple/{id}/answers"""
    adapter = CoupleIntegrationAdapter(db_session)

    def handler(couple_id: str, user_a_answers: Dict[int, int], user_b_answers: Dict[int, int]) -> Dict:
        return adapter.process_couple_answers(couple_id, user_a_answers, user_b_answers, generate_pdf=True)

    return handler


if __name__ == "__main__":
    # Test simplificado
    adapter = CoupleIntegrationAdapter(db_session=None)

    test_answers_a = {i: 3 for i in range(1, 501)}
    test_answers_b = {i: 3 for i in range(1, 501)}
    test_answers_a[1] = 25  # Tiene hijos
    test_answers_a[500] = 75  # High-ticket willing

    result = adapter.process_couple_answers(
        "TEST-001",
        test_answers_a,
        test_answers_b,
        generate_pdf=True
    )

    print("✅ Integration test completed:")
    print(f"  Compatibility: {result['compatibility_score']}%")
    print(f"  Shield Score: {result['shield_score']}%")
    print(f"  Runway: {result['runway_days']} days")
    print(f"  High-ticket trigger: {result['high_ticket_trigger']}")
    print(f"  PDF URL: {result['pdf_url']}")
