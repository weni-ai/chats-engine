# SUBSTITUA TODO O CONTEÚDO de: chats/apps/sectors/tests/test_bug_investigation.py

import json
import threading
import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from chats.apps.api.v1.sectors.serializers import SectorSerializer
from chats.apps.api.v1.sectors.viewsets import SectorViewset
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector

User = get_user_model()


class BugInvestigationTest(TestCase):
    """
    Teste para provar a tese de que a duplicação de secondary_project no config
    + múltiplos saves causam o campo dedicado ficar NULL
    """

    def setUp(self):
        """Setup executado antes de CADA teste"""
        self.factory = APIRequestFactory()
        
        # Cria projeto principal
        self.project = Project.objects.create(
            name="Test Project",
            timezone="America/Sao_Paulo",
            config={"its_principal": True},
        )
        
        # Cria usuário
        self.user = User.objects.create_user(
            email="test@test.com",
            password="test123",
        )
        
        # Cria permissão
        self.permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=3,
        )

    @patch('chats.apps.api.v1.sectors.viewsets.FlowRESTClient')
    @patch('chats.apps.api.v1.sectors.viewsets.IntegratedTicketers')
    def test_bug_duplication_causes_null_field(self, mock_integrated, mock_flows):
        """
        Testa o bug completo:
        1. Serializer com .get() causa duplicação
        2. Viewset executa ambas operações
        3. _mark_ticketer_integrated faz save(update_fields=["config"])
        4. Campo dedicado secondary_project fica NULL/perdido
        """
        
        # Mock do flows_client.create_ticketer
        mock_flows_instance = Mock()
        mock_flows_instance.create_ticketer.return_value = Mock(
            status_code=status.HTTP_201_CREATED
        )
        mock_flows.return_value = mock_flows_instance
        
        # Mock do integrate_individual_ticketer para simular o comportamento real
        def side_effect_integrate(project, secondary_project):
            print("\n🔍 [INTEGRATE] integrate_individual_ticketer chamado!")
            print(f"   secondary_project recebido: {secondary_project}")
            
            # Simula o que acontece dentro do integrate_individual_ticketer
            sector = Sector.objects.get(
                project=project,
                secondary_project__uuid=secondary_project.get("uuid") if isinstance(secondary_project, dict) else secondary_project
            )
            
            print(f"\n📊 [INTEGRATE] Setor buscado do banco:")
            print(f"   sector.uuid: {sector.uuid}")
            print(f"   sector.secondary_project: {sector.secondary_project}")
            print(f"   sector.config: {sector.config}")
            
            # Simula _mark_ticketer_integrated
            sector_for_mark = Sector.objects.get(uuid=sector.uuid)
            config = sector_for_mark.config or {}
            config["ticketer_integrated"] = True
            sector_for_mark.config = config
            
            print(f"\n💾 [MARK] Antes do save(update_fields=['config']):")
            print(f"   sector_for_mark.secondary_project: {sector_for_mark.secondary_project}")
            print(f"   sector_for_mark.config: {sector_for_mark.config}")
            
            # ⚠️ ESTE É O SAVE PROBLEMÁTICO
            sector_for_mark.save(update_fields=["config"])
            
            print(f"\n💾 [MARK] Depois do save(update_fields=['config']):")
            sector_for_mark.refresh_from_db()
            print(f"   sector_for_mark.secondary_project: {sector_for_mark.secondary_project}")
            print(f"   sector_for_mark.config: {sector_for_mark.config}")
        
        mock_integrated_instance = Mock()
        mock_integrated_instance.integrate_individual_ticketer.side_effect = side_effect_integrate
        mock_integrated.return_value = mock_integrated_instance
        
        # Dados do request
        data = {
            "uuid": "f844309f-2003-41c4-ba9c-0543f4d98c10",
            "name": "teste",
            "can_edit_custom_fields": True,
            "can_trigger_flows": True,
            "config": {
                "secondary_project": "2c677ac3-858a-4957-b536-c0d4f92abbb3"
            },
            "project": str(self.project.uuid),
            "rooms_limit": "0",
            "sign_messages": True,
            "work_start": None,
            "work_end": None,
            "open_offline": True,
            "working_day": None,
            "required_tags": False,
            "automatic_message": {
                "is_active": False,
                "text": ""
            }
        }
        
        print("\n" + "="*80)
        print("🚀 INÍCIO DO TESTE - SIMULANDO FLUXO DE PRODUÇÃO")
        print("="*80)
        
        # Cria request
        request = self.factory.post(
            '/v1/sector/',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.user
        
        # Serializer
        serializer = SectorSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        print("\n📝 [SERIALIZER] validated_data após validate():")
        print(f"   secondary_project: {serializer.validated_data.get('secondary_project')}")
        print(f"   config: {serializer.validated_data.get('config')}")
        
        # ⚠️ AQUI ESTÁ O PROBLEMA: config AINDA TEM secondary_project por causa do .get()
        if 'secondary_project' in serializer.validated_data.get('config', {}):
            print("\n❌ [BUG CONFIRMADO] secondary_project DUPLICADO no config!")
        
        # Viewset perform_create
        viewset = SectorViewset()
        viewset.request = request
        viewset.format_kwarg = None
        
        print("\n🔄 [VIEWSET] Executando perform_create...")
        viewset.perform_create(serializer)
        
        # Verifica o estado final
        sector = Sector.objects.get(uuid=data["uuid"])
        
        print("\n" + "="*80)
        print("📊 RESULTADO FINAL DO BANCO DE DADOS")
        print("="*80)
        print(f"sector.uuid: {sector.uuid}")
        print(f"sector.secondary_project: {sector.secondary_project}")
        print(f"sector.config: {sector.config}")
        print("\n")
        
        # Verificações
        if sector.secondary_project is None:
            print("💥 BUG REPRODUZIDO: secondary_project está NULL!")
            print("   Causa: duplicação no config + save(update_fields=['config'])")
        else:
            print("✅ Campo secondary_project preservado")
        
        if "secondary_project" in (sector.config or {}):
            print("⚠️  secondary_project ainda está no config (duplicado)")
        
        # Assertions
        self.assertIsNotNone(
            sector.secondary_project,
            "BUG: secondary_project ficou NULL devido à duplicação + múltiplos saves"
        )
        self.assertNotIn(
            "secondary_project",
            sector.config or {},
            "BUG: secondary_project ainda está duplicado no config"
        )

    @patch('chats.apps.api.v1.sectors.viewsets.FlowRESTClient')
    @patch('chats.apps.api.v1.sectors.viewsets.IntegratedTicketers')
    def test_bug_race_condition_causes_null(self, mock_integrated, mock_flows):
        """
        Testa race condition: múltiplos saves concorrentes causam perda do campo.
        Simula ambiente Gunicorn com workers concorrentes.
        """
        
        # Mock flows
        mock_flows_instance = Mock()
        mock_flows_instance.create_ticketer.return_value = Mock(
            status_code=status.HTTP_201_CREATED
        )
        mock_flows.return_value = mock_flows_instance
        
        results = {"thread1_secondary": None, "thread2_secondary": None, "errors": []}
        
        def simulate_mark_ticketer_integrated(sector_uuid, thread_name):
            """Simula _mark_ticketer_integrated por diferentes workers"""
            try:
                from django.db import connection
                connection.close()
                
                print(f"\n🔄 [{thread_name}] Iniciando save concorrente...")
                
                sector = Sector.objects.get(uuid=sector_uuid)
                
                print(f"📊 [{thread_name}] Setor buscado:")
                print(f"   secondary_project ANTES: {sector.secondary_project}")
                print(f"   config ANTES: {sector.config}")
                
                time.sleep(0.05)
                
                config = sector.config or {}
                config[f"flag_{thread_name}"] = True
                sector.config = config
                
                print(f"💾 [{thread_name}] Executando save(update_fields=['config'])...")
                sector.save(update_fields=["config"])
                
                sector.refresh_from_db()
                
                print(f"✅ [{thread_name}] DEPOIS do save:")
                print(f"   secondary_project: {sector.secondary_project}")
                print(f"   config: {sector.config}")
                
                results[f"{thread_name}_secondary"] = sector.secondary_project
                
            except Exception as e:
                print(f"❌ [{thread_name}] ERRO: {e}")
                results["errors"].append(f"{thread_name}: {str(e)}")
        
        def side_effect_integrate(project, secondary_project):
            sector = Sector.objects.get(
                project=project,
                secondary_project__uuid=secondary_project.get("uuid")
            )
            simulate_mark_ticketer_integrated(str(sector.uuid), "thread1")
        
        mock_integrated_instance = Mock()
        mock_integrated_instance.integrate_individual_ticketer.side_effect = side_effect_integrate
        mock_integrated.return_value = mock_integrated_instance
        
        data = {
            "uuid": "aaaaaaaa-0003-41c4-ba9c-0543f4d98c10",
            "name": "teste race condition",
            "can_edit_custom_fields": True,
            "can_trigger_flows": True,
            "config": {
                "secondary_project": "2c677ac3-858a-4957-b536-c0d4f92abbb3"
            },
            "project": str(self.project.uuid),
            "rooms_limit": "0",
            "sign_messages": True,
            "required_tags": False,
        }
        
        print("\n" + "="*80)
        print("🚀 TESTE COM RACE CONDITION - MÚLTIPLOS WORKERS")
        print("="*80)
        
        request = self.factory.post('/v1/sector/', data=json.dumps(data), content_type='application/json')
        request.user = self.user
        
        serializer = SectorSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        print("\n📝 [SERIALIZER] validated_data:")
        print(f"   secondary_project: {serializer.validated_data.get('secondary_project')}")
        print(f"   config: {serializer.validated_data.get('config')}")
        
        if 'secondary_project' in serializer.validated_data.get('config', {}):
            print("\n⚠️  [DUPLICAÇÃO] secondary_project no config!")
        
        viewset = SectorViewset()
        viewset.request = request
        viewset.format_kwarg = None
        
        print("\n🔄 [VIEWSET] Criando setor e chamando integrate (thread1)...")
        viewset.perform_create(serializer)
        
        time.sleep(0.2)
        
        print("\n🔄 [WORKER 2] Simulando segundo worker acessando mesmo setor...")
        thread2 = threading.Thread(
            target=simulate_mark_ticketer_integrated,
            args=(data["uuid"], "thread2")
        )
        thread2.start()
        thread2.join()
        
        sector = Sector.objects.get(uuid=data["uuid"])
        
        print("\n" + "="*80)
        print("📊 RESULTADO FINAL APÓS RACE CONDITION")
        print("="*80)
        print(f"sector.uuid: {sector.uuid}")
        print(f"sector.secondary_project: {sector.secondary_project}")
        print(f"sector.config: {sector.config}")
        print(f"\nThread1 viu secondary_project: {results['thread1_secondary']}")
        print(f"Thread2 viu secondary_project: {results['thread2_secondary']}")
        
        if results["errors"]:
            print(f"\n❌ Erros: {results['errors']}")
        
        print("\n")
        
        if sector.secondary_project is None:
            print("💥 RACE CONDITION REPRODUZIDA: secondary_project perdido!")
        else:
            print("⚠️  Campo preservado, mas duplicação no config permanece")
        
        if "secondary_project" in (sector.config or {}):
            print("❌ secondary_project duplicado no config")
            print("   RISCO: Em produção com PostgreSQL + Gunicorn, isso pode causar NULL")

    @patch('chats.apps.api.v1.sectors.viewsets.FlowRESTClient')
    @patch('chats.apps.api.v1.sectors.viewsets.IntegratedTicketers')  
    def test_bug_transaction_isolation_issue(self, mock_integrated, mock_flows):
        """
        Testa problema de isolamento de transação:
        Save parcial com update_fields pode perder dados em transações concorrentes
        """
        
        mock_flows_instance = Mock()
        mock_flows_instance.create_ticketer.return_value = Mock(
            status_code=status.HTTP_201_CREATED
        )
        mock_flows.return_value = mock_flows_instance
        
        def side_effect_integrate(project, secondary_project):
            print("\n🔍 [INTEGRATE] Iniciando...")
            
            sector = Sector.objects.get(
                project=project,
                secondary_project__uuid=secondary_project.get("uuid")
            )
            
            print(f"📊 [GET 1] Setor buscado por secondary_project:")
            print(f"   uuid: {sector.uuid}")
            print(f"   secondary_project: {sector.secondary_project}")
            print(f"   config: {sector.config}")
            
            sector2 = Sector.objects.get(uuid=sector.uuid)
            
            print(f"\n📊 [GET 2] Setor buscado por uuid:")
            print(f"   secondary_project: {sector2.secondary_project}")
            print(f"   config: {sector2.config}")
            
            config = sector2.config or {}
            config["ticketer_integrated"] = True
            sector2.config = config
            
            print(f"\n💾 [SAVE] Salvando APENAS config...")
            print(f"   ANTES - secondary_project: {sector2.secondary_project}")
            print(f"   ANTES - config: {sector2.config}")
            
            sector2.save(update_fields=["config"])
            
            sector2.refresh_from_db()
            print(f"\n💾 [APÓS SAVE] refresh_from_db:")
            print(f"   secondary_project: {sector2.secondary_project}")
            print(f"   config: {sector2.config}")
            
            sector3 = Sector.objects.get(uuid=sector.uuid)
            print(f"\n📊 [GET 3] Nova busca do banco:")
            print(f"   secondary_project: {sector3.secondary_project}")
            print(f"   config: {sector3.config}")
        
        mock_integrated_instance = Mock()
        mock_integrated_instance.integrate_individual_ticketer.side_effect = side_effect_integrate
        mock_integrated.return_value = mock_integrated_instance
        
        data = {
            "uuid": "bbbbbbbb-0003-41c4-ba9c-0543f4d98c10",
            "name": "teste transaction",
            "can_edit_custom_fields": True,
            "can_trigger_flows": True,
            "config": {
                "secondary_project": "2c677ac3-858a-4957-b536-c0d4f92abbb3"
            },
            "project": str(self.project.uuid),
            "rooms_limit": "0",
            "sign_messages": True,
            "required_tags": False,
        }
        
        print("\n" + "="*80)
        print("🚀 TESTE DE ISOLAMENTO DE TRANSAÇÃO")
        print("="*80)
        
        request = self.factory.post('/v1/sector/', data=json.dumps(data), content_type='application/json')
        request.user = self.user
        
        serializer = SectorSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        print("\n📝 [SERIALIZER] validated_data COM DUPLICAÇÃO:")
        print(f"   secondary_project: {serializer.validated_data.get('secondary_project')}")
        print(f"   config: {serializer.validated_data.get('config')}")
        
        viewset = SectorViewset()
        viewset.request = request
        viewset.format_kwarg = None
        
        print("\n🔄 [VIEWSET] Executando perform_create (múltiplos gets/saves)...")
        viewset.perform_create(serializer)
        
        sector_final = Sector.objects.get(uuid=data["uuid"])
        
        print("\n" + "="*80)
        print("📊 ESTADO FINAL NO BANCO")
        print("="*80)
        print(f"secondary_project: {sector_final.secondary_project}")
        print(f"config: {sector_final.config}")
        
        if sector_final.secondary_project is None:
            print("\n💥 BUG CRÍTICO: Campo secondary_project PERDIDO!")
            print("   Causa: save(update_fields=['config']) com duplicação")
        
        if "secondary_project" in (sector_final.config or {}):
            print("\n❌ DUPLICAÇÃO CONFIRMADA no config")
            print("   Em produção (PostgreSQL + múltiplos workers), isso causa NULL!")

    @patch('chats.apps.api.v1.sectors.viewsets.FlowRESTClient')
    @patch('chats.apps.api.v1.sectors.viewsets.IntegratedTicketers')
    def test_endpoint_path_perform_create_persists_secondary_project(self, mock_integrated, mock_flows):
        """
        Usa exatamente o caminho do endpoint: SectorViewset.perform_create,
        garantindo que após serializer.save() o campo dedicado secondary_project
        esteja persistido no banco.
        """
        # Mocks integrações
        mock_flows_instance = Mock()
        mock_flows_instance.create_ticketer.return_value = Mock(
            status_code=status.HTTP_201_CREATED
        )
        mock_flows.return_value = mock_flows_instance

        mock_integrated_instance = Mock()
        mock_integrated_instance.integrate_individual_ticketer.return_value = {"status": "success"}
        mock_integrated.return_value = mock_integrated_instance

        # Dados do request (igual produção)
        data = {
            "uuid": "99999999-0003-41c4-ba9c-0543f4d98c10",
            "name": "teste perform_create",
            "can_edit_custom_fields": True,
            "can_trigger_flows": True,
            "config": {
                "secondary_project": "2c677ac3-858a-4957-b536-c0d4f92abbb3"
            },
            "project": str(self.project.uuid),
            "rooms_limit": "0",
            "sign_messages": True,
            "work_start": None,
            "work_end": None,
            "open_offline": True,
            "working_day": None,
            "required_tags": False,
            "automatic_message": {
                "is_active": False,
                "text": ""
            }
        }

        print("\n" + "="*80)
        print("🚀 TESTE ENDPOINT - perform_create")
        print("="*80)

        # Cria request e serializer
        request = self.factory.post(
            '/v1/sector/',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.user

        serializer = SectorSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        print("\n📝 [SERIALIZER] validated_data:")
        print(f"   secondary_project: {serializer.validated_data.get('secondary_project')}")
        print(f"   config: {serializer.validated_data.get('config')}")

        # Viewset perform_create
        viewset = SectorViewset()
        viewset.request = request
        viewset.format_kwarg = None

        print("\n🔄 [VIEWSET] Executando perform_create...")
        viewset.perform_create(serializer)

        # Verifica imediatamente no banco
        sector = Sector.objects.get(uuid=data["uuid"]) 
        print("\n📦 [DB] Após perform_create:")
        print(f"   secondary_project: {sector.secondary_project}")
        print(f"   config: {sector.config}")

        # O campo dedicado deve estar presente após o save
        self.assertIsNotNone(
            sector.secondary_project,
            "secondary_project ficou None após perform_create (serializer.save())"
        )

        # E a busca por json path deve encontrar
        token_uuid = serializer.validated_data["secondary_project"]["uuid"]
        self.assertTrue(
            Sector.objects.filter(project=self.project, secondary_project__uuid=token_uuid).exists(),
            "Não encontrou setor pelo campo dedicado após perform_create"
        )