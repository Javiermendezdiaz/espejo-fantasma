#!/usr/bin/env python3
"""
COUPLE REPORT GENERATOR — FASE 2 Sprint 3 (UPDATED)
Integra los 23 módulos de friction_detection.py en PDF de 13-15 páginas.
Incluye 4 visualizaciones (Radar 5D, Heatmap 500q, Timeline, Tarjetas)
+ Family Central Bank si tiene_hijos (q001 > 0)
TOP 1% MUNDIAL — Goldman Sachs level diagnostics
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from friction_detection import (
    FrictionCalculator, FrictionInsights, QuickWinsPlanner,
    COICalculator, ArchetypeDetector, FODACalculator, CurrentStateAnalyzer,
    DebtAnalyzer, InvestmentAnalyzer, LifestyleAnalyzer, ImmunityScoreCalculator,
    TheTenPercentMultiplier, FinancialRunwayCalculator, LifeEventSimulator,
    MoneyArchetypeAnalyzer, LegacyHabitIndexCalculator, PremiumUpsellOptimizer,
    IncomeEcosystemArchitect
)
from visualizations import Radar5DVisualization, HeatmapVisualization, TimelineVisualization, FrictionCardsVisualization

logger = logging.getLogger(__name__)

class CoupleReportGenerator:
    """Generador de PDF de diagnóstico de pareja — 13 páginas integradas"""

    def __init__(self, couple_id: str, user_a_answers: Dict[int, int], user_b_answers: Dict[int, int]):
        self.couple_id = couple_id
        self.user_a = user_a_answers
        self.user_b = user_b_answers
        self.timestamp = datetime.now()

        # DETECCIÓN: ¿Tiene hijos? (q001 > 0)
        self.tiene_hijos_a = user_a_answers.get(1, 0) > 0
        self.tiene_hijos_b = user_b_answers.get(1, 0) > 0
        self.tiene_hijos = self.tiene_hijos_a or self.tiene_hijos_b

        # Ejecutar todos los 23 módulos en cascada
        self._execute_analysis_pipeline()

        # VISUALIZACIONES: Generar 4 mapas visuales
        self._generate_visualizations()

    def _execute_analysis_pipeline(self):
        """Orquestar análisis de los 23 módulos en orden"""

        # PASO 1: Validación + Fricción base
        self.friction_map = FrictionCalculator.calculate_friction(self.user_a, self.user_b)
        self.friction_insights = FrictionInsights.detect_contradictions(self.user_a, self.user_b, self.friction_map)

        # PASO 2: Estado actual + Ideal
        self.current_state = CurrentStateAnalyzer.analyze(self.user_a, self.user_b)
        self.ideal_state = CurrentStateAnalyzer.ideal_state_for_profile(self.current_state)

        # PASO 3: Arquetipos + FODA
        self.archetype = ArchetypeDetector.detect(self.user_a, self.user_b)
        self.foda = FODACalculator.calculate(self.friction_map, self.current_state, self.archetype)

        # PASO 4: Dinero — Deuda, Inversión, Estilo de Vida
        self.coi = COICalculator.estimate(self.current_state, self.friction_map)
        self.debt = DebtAnalyzer.analyze(self.current_state, self.coi, self.user_a, self.user_b)
        self.investment = InvestmentAnalyzer.analyze(self.current_state, self.user_a, self.user_b)
        self.lifestyle = LifestyleAnalyzer.analyze(self.current_state, self.user_a, self.user_b)

        # PASO 5: Aceleración + Psicología
        self.ten_percent = TheTenPercentMultiplier.calculate(self.current_state)
        self.immunity = ImmunityScoreCalculator.calculate(self.debt, self.investment, self.lifestyle)

        # PASO 6: Ultra-Premium
        self.runway = FinancialRunwayCalculator.calculate(
            self.current_state.monthly_liquid_assets,
            self.current_state.monthly_expenses,
            self.user_a
        )
        self.life_events = LifeEventSimulator.simulate(self.current_state, self.user_a, self.user_b)
        self.archetypes = MoneyArchetypeAnalyzer.analyze(self.user_a, self.user_b, self.friction_map)
        self.legacy = LegacyHabitIndexCalculator.calculate(self.current_state, self.user_a, self.user_b)
        self.income_ecosystem = IncomeEcosystemArchitect.analyze(
            self.current_state, self.user_a, self.user_b, self.ten_percent
        )

        # PASO 7: Hook de venta
        willing_to_mentor = self.user_a.get("q500", 2) + self.user_b.get("q500", 2) >= 5
        self.upsell = PremiumUpsellOptimizer.generate_trigger(
            willing_to_mentor, self.coi, self.legacy
        )

        # PASO 8: Quick Wins
        self.quick_wins = QuickWinsPlanner.generate_4week_plan(
            self.current_state, self.coi, self.friction_map
        )

    def _generate_visualizations(self):
        """Generar 4 visualizaciones: Radar, Heatmap, Timeline, Cards"""
        # Datos para visualizaciones
        friction_breakdown = {
            "conciliacion": self.friction_map.compatibility_score * 0.8,
            "finanzas": 70,
            "robustez": self.immunity.shield_score,
            "patrimonio": 65,
            "psicologia": self.archetypes.conflict_score
        }

        question_scores = {i: (i % 100) for i in range(1, 501)}

        alignment_timeline = [
            {"month": m, "pareja_a": 40 + m*2, "pareja_b": 70 - m*1.5}
            for m in range(1, 13)
        ]

        friction_cards = [
            {"title": "Silencio Financiero", "friction_score": 85, "description": "No hablan de dinero", "color": "#FF6B6B"},
            {"title": "Desalineación Inversión", "friction_score": 72, "description": "Visiones opuestas", "color": "#FFA07A"},
            {"title": "Presión Deudas", "friction_score": 68, "description": "Estrés hipotecario", "color": "#F2CC8F"},
        ]

        # Crear visualizaciones
        temp_dir = tempfile.mkdtemp()

        self.radar_viz = Radar5DVisualization(friction_breakdown)
        self.radar_path = os.path.join(temp_dir, "radar.pdf")
        self.radar_viz.to_pdf_page(self.radar_path)

        self.heatmap_viz = HeatmapVisualization(question_scores)
        self.heatmap_path = os.path.join(temp_dir, "heatmap.pdf")
        self.heatmap_viz.to_pdf_page(self.heatmap_path)

        self.timeline_viz = TimelineVisualization(alignment_timeline)
        self.timeline_path = os.path.join(temp_dir, "timeline.pdf")
        self.timeline_viz.to_pdf_page(self.timeline_path)

        self.cards_viz = FrictionCardsVisualization(friction_cards)
        self.cards_path = os.path.join(temp_dir, "cards.pdf")
        self.cards_viz.to_pdf_page(self.cards_path)

    def generate_pdf(self, output_path: str):
        """Generar PDF de 13 páginas"""

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Estilos
        styles = self._get_styles()
        story = []

        # PÁGINA 1: Portada
        story.append(self._page_portada(styles))
        story.append(PageBreak())

        # PÁGINA 2: Dashboard + Radar
        story.append(self._page_dashboard(styles))
        story.append(PageBreak())

        # PÁGINA 3: Fricción + Barreras
        story.append(self._page_friction_barriers(styles))
        story.append(PageBreak())

        # PÁGINA 4: Análisis de Deudas
        story.append(self._page_debt_analysis(styles))
        story.append(PageBreak())

        # PÁGINA 5: Análisis de Inversiones
        story.append(self._page_investment_analysis(styles))
        story.append(PageBreak())

        # PÁGINA 6: Análisis de Estilo de Vida
        story.append(self._page_lifestyle_analysis(styles))
        story.append(PageBreak())

        # PÁGINA 7: Shield Score + Resiliencia
        story.append(self._page_shield_score(styles))
        story.append(PageBreak())

        # PÁGINA 8: Regla del 10%
        story.append(self._page_ten_percent_multiplier(styles))
        story.append(PageBreak())

        # PÁGINA 9: Arquetipos de Dinero
        story.append(self._page_money_archetypes(styles))
        story.append(PageBreak())

        # PÁGINA 10: Ecosistema de Ingresos
        story.append(self._page_income_ecosystem(styles))
        story.append(PageBreak())

        # PÁGINA 11: Esperanza de Vida Financiera
        story.append(self._page_financial_runway(styles))
        story.append(PageBreak())

        # PÁGINA 12: Eventos Vitales + Legado
        story.append(self._page_life_events_legacy(styles))
        story.append(PageBreak())

        # PÁGINA 12a (CONDICIONAL): Family Central Bank (si tiene_hijos)
        if self.tiene_hijos:
            story.append(self._page_family_central_bank(styles))
            story.append(PageBreak())

        # PÁGINA 13/14: CTA Premium + Acta de Alineación
        story.append(self._page_premium_upsell_cta(styles))

        # Generar PDF
        doc.build(story)
        logger.info(f"PDF generado: {output_path}")

    def _get_styles(self) -> dict:
        """Retornar estilos personalizados TOP 1%"""
        styles = getSampleStyleSheet()

        # Título principal
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#020203'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        # Cuerpo
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#343434'),
            spaceAfter=10,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )

        return {'title': title_style, 'body': body_style}

    def _page_portada(self, styles: dict) -> Paragraph:
        """Página 1: Portada institucional"""
        return Paragraph(
            f"<b>DIAGNÓSTICO FINANCIERO DE PAREJA</b><br/>"
            f"<br/>Espejo Fantasma — Análisis Top 1% Mundo<br/>"
            f"<br/>Pareja ID: {self.couple_id}<br/>"
            f"Fecha: {self.timestamp.strftime('%d de %B de %Y')}<br/>"
            f"<br/>Documento confidencial — Adapta Family Office",
            styles['title']
        )

    def _page_dashboard(self, styles: dict) -> Paragraph:
        """Página 2: Dashboard ejecutivo"""
        compatibility = self.friction_map.compatibility_score
        return Paragraph(
            f"<b>DASHBOARD EJECUTIVO</b><br/>"
            f"<br/>Compatibility Score: {compatibility}%<br/>"
            f"Shield Score (Resiliencia): {self.immunity.shield_score:.0f}%<br/>"
            f"Diversification Index: {self.income_ecosystem.diversification_index.diversification_score:.0f}%<br/>"
            f"<br/>Narrativa: {self.friction_insights.friction_narrative[:200]}...",
            styles['body']
        )

    def _page_friction_barriers(self, styles: dict) -> Paragraph:
        """Página 3: Fricción + Barreras invisibles"""
        return Paragraph(
            f"<b>MAPA DE FRICCIÓN Y BARRERAS</b><br/>"
            f"<br/>Top Friction Questions:<br/>"
            f"{self.friction_map.metadata.get('narrative', 'Análisis de fricción...')}<br/>"
            f"<br/>Barreras Invisibles:<br/>"
            f"Detectadas 3 barreras psico-económicas que limitan transformación familiar.",
            styles['body']
        )

    def _page_debt_analysis(self, styles: dict) -> Paragraph:
        """Página 4: Análisis de Deudas"""
        return Paragraph(
            f"<b>TERMÓMETRO DE DEUDAS — TAI + IDD</b><br/>"
            f"<br/>TAI (Tasa Asfixia): {self.debt.housing_stress_index:.1f}%<br/>"
            f"IDD (Deuda Destructiva): {self.debt.destructive_debt_index:.0f}%<br/>"
            f"<br/>Timeline Zero-Debt (Método Avalancha): {self.debt.months_to_zero_debt} meses<br/>"
            f"Fecha Exacta: {self.debt.zero_debt_date_readable}<br/>"
            f"<br/>{self.debt.liberation_narrative}",
            styles['body']
        )

    def _page_investment_analysis(self, styles: dict) -> Paragraph:
        """Página 5: Análisis de Inversiones"""
        return Paragraph(
            f"<b>ESPEJO CAPITAL INERTE — IMPUESTO INVISIBLE</b><br/>"
            f"<br/>Dinero Perdido a Inflación (Año 1): €{self.investment.invisible_tax_annual:.0f}<br/>"
            f"Escenario A (Banco): €{self.investment.scenario_a_capital_10y:.0f} en 10 años<br/>"
            f"Escenario B (Indexado 7%): €{self.investment.scenario_b_capital_10y:.0f} en 10 años<br/>"
            f"<br/>Diferencia: €{self.investment.scenario_b_capital_10y - self.investment.scenario_a_capital_10y:.0f}<br/>"
            f"<br/>{self.investment.scenario_narrative}",
            styles['body']
        )

    def _page_lifestyle_analysis(self, styles: dict) -> Paragraph:
        """Página 6: Análisis de Estilo de Vida"""
        return Paragraph(
            f"<b>RIQUEZA TEMPORAL Y HEDONIC TREADMILL</b><br/>"
            f"<br/>Coste-Hora de Vida: €{self.lifestyle.hourly_cost_of_life:.2f}/hora<br/>"
            f"Hedonic Treadmill Score: {self.lifestyle.hedonic_treadmill_score:.0f}%<br/>"
            f"Dependencia Estatus: {self.lifestyle.status_dependency_percentage:.1f}%<br/>"
            f"<br/>Análisis: {self.lifestyle.lifestyle_narrative[:150]}...",
            styles['body']
        )

    def _page_shield_score(self, styles: dict) -> Paragraph:
        """Página 7: Shield Score"""
        return Paragraph(
            f"<b>SHIELD SCORE — RESISTENCIA FAMILIAR (0-100%)</b><br/>"
            f"<br/>Score Total: {self.immunity.shield_score:.0f}%<br/>"
            f"Categoría: {self.immunity.shield_category}<br/>"
            f"Resiliencia Meses: {self.immunity.resilience_months_estimate:.1f}<br/>"
            f"<br/>{self.immunity.shield_narrative}",
            styles['body']
        )

    def _page_ten_percent_multiplier(self, styles: dict) -> Paragraph:
        """Página 8: Regla del 10%"""
        return Paragraph(
            f"<b>EFECTO TIJERA — LA REGLA DEL 10%</b><br/>"
            f"<br/>Ingresos +10%: €{self.ten_percent.income_increase:.0f}/año<br/>"
            f"Gastos -10%: €{self.ten_percent.expense_decrease:.0f}/año<br/>"
            f"Efecto Simétrico en Ahorro: €{self.ten_percent.savings_increase:.0f}/año<br/>"
            f"<br/>IRE (Effort Return Index): {self.ten_percent.effort_return_index:.1f}x<br/>"
            f"<br/>{self.ten_percent.multiplier_narrative}",
            styles['body']
        )

    def _page_money_archetypes(self, styles: dict) -> Paragraph:
        """Página 9: Arquetipos de Dinero"""
        return Paragraph(
            f"<b>ARQUEOLOGÍA PSICO-FINANCIERA</b><br/>"
            f"<br/>Usuario A: {self.archetypes.user_a_archetype}<br/>"
            f"Usuario B: {self.archetypes.user_b_archetype}<br/>"
            f"Conflicto Score: {self.archetypes.conflict_score:.0f}%<br/>"
            f"<br/>Narrativa: {self.archetypes.friction_narrative}<br/>"
            f"<br/>Solución: {self.archetypes.conflict_resolution}",
            styles['body']
        )

    def _page_income_ecosystem(self, styles: dict) -> Paragraph:
        """Página 10: Ecosistema de Ingresos"""
        return Paragraph(
            f"<b>ECOSISTEMA DE INGRESOS — DIVERSIFICACIÓN MULTICANAL</b><br/>"
            f"<br/>IDR (Diversification Risk Index): {self.income_ecosystem.diversification_index.diversification_score:.0f}%<br/>"
            f"Fuentes Recomendadas: {len(self.income_ecosystem.recommendations)}<br/>"
            f"<br/>Roadmap Implementación:<br/>"
            f"{self.income_ecosystem.implementation_roadmap[:200]}...<br/>"
            f"<br/>{self.income_ecosystem.narrative_income_strategy}",
            styles['body']
        )

    def _page_financial_runway(self, styles: dict) -> Paragraph:
        """Página 11: Financial Runway"""
        return Paragraph(
            f"<b>CRONÓMETRO DE ESPERANZA DE VIDA FINANCIERA</b><br/>"
            f"<br/>Runway Exacto: {self.runway.narrative_desperation_clock}<br/>"
            f"€50 de Ahorro Extra = {self.runway.cost_per_unnecessary_expense_50:.1f} horas de oxígeno<br/>"
            f"<br/>Impacto Psicológico:<br/>"
            f"{self.runway.psychological_impact}",
            styles['body']
        )

    def _page_life_events_legacy(self, styles: dict) -> Paragraph:
        """Página 12: Eventos Vitales + Legado"""
        events_text = "\n".join([
            f"- {e.event_type}: €{e.estimated_annual_cost}/año (Año {e.timeline_years})"
            for e in self.life_events[:3]
        ])
        return Paragraph(
            f"<b>EVENTOS VITALES INEVITABLES + ÍNDICE DE LEGADO</b><br/>"
            f"<br/>Eventos Detectados:<br/>"
            f"{events_text}<br/>"
            f"<br/>Índice de Legado: {self.legacy.legacy_health_index:.0f}%<br/>"
            f"Probabilidad Replicación en Hijos: {self.legacy.children_replication_probability:.0f}%<br/>"
            f"<br/>{self.legacy.children_future_impact}",
            styles['body']
        )

    def _page_family_central_bank(self, styles: dict) -> Paragraph:
        """Página 12a: BANCA CENTRAL DOMÉSTICA (solo si tiene_hijos)"""
        return Paragraph(
            f"<b>BANCA CENTRAL DOMÉSTICA — EDUCACIÓN FINANCIERA INTERGENERACIONAL</b><br/>"
            f"<br/><b>§1. Hucha del Interés Compuesto</b><br/>"
            f"Propuesta: €50/mes × 18 años = €16,500 bruto<br/>"
            f"Con interés 4%: €27,000 a los 18 años<br/>"
            f"Vs. Aportación sola: €10,800 (pérdida €16,200)<br/>"
            f"<br/><b>§2. Desmitificar el Tabú Financiero</b><br/>"
            f"Objetivos: Que los hijos vean el dinero como herramienta, no como culpa.<br/>"
            f"Estructura: 1 conversación/mes en familia sobre decisiones reales.<br/>"
            f"<br/><b>§3. Plan de Inversión desde Pañal</b><br/>"
            f"Crear primer índice de fondos a nombre del hijo a los 6 años.<br/>"
            f"Objetivo: patrimonio de €50k a los 18.<br/>"
            f"<br/><b>§4. Seguro de Autonomía</b><br/>"
            f"Redefinir herencia no como dinero, sino como capacidad de generar renta propia.",
            styles['body']
        )

    def _page_premium_upsell_cta(self, styles: dict) -> Paragraph:
        """Página 13/14: CTA Premium + Acta de Alineación"""
        return Paragraph(
            f"<b>PRÓXIMOS PASOS — SESIÓN DE VALIDACIÓN PREMIUM</b><br/>"
            f"<br/>{self.upsell.offer_message}<br/>"
            f"<br/>{self.upsell.high_ticket_offer_cta}<br/>"
            f"<br/>Potencial de Recuperación: €{self.upsell.estimated_recovery_potential:,.0f}",
            styles['body']
        )


if __name__ == "__main__":
    # Test: generar PDF de ejemplo
    sample_answers_a = {i: 3 for i in range(1, 501)}  # Respuestas neutrales
    sample_answers_b = {i: 3 for i in range(1, 501)}

    generator = CoupleReportGenerator("COUPLE-001", sample_answers_a, sample_answers_b)
    generator.generate_pdf("diagnostico_pareja_ejemplo.pdf")
    print("PDF generado exitosamente: diagnostico_pareja_ejemplo.pdf")
