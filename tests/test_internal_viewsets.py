from django.test import SimpleTestCase

from chats.apps.api.v1.internal.sectors.viewsets import SectorInternalViewset


class DummySectorViewset(SectorInternalViewset):
    """Isolated version where we can manipulate the `action` attribute."""

    def __init__(self, action):
        # Avoid running default DRF initialisation logic
        self.action = action


class SectorInternalViewsetTests(SimpleTestCase):
    def test_get_serializer_class_returns_expected(self):
        # Parametrização convertida para um loop
        test_cases = [
            ("list", "SectorReadOnlyListSerializer"),
            ("retrieve", "SectorReadOnlyRetrieveSerializer"),
            ("update", "SectorUpdateSerializer"),
            ("create", SectorInternalViewset.serializer_class),
        ]
        
        for action, expected_serializer_cls in test_cases:
            with self.subTest(action=action):
                # Arrange
                view = DummySectorViewset(action)
                
                # Act
                serializer_cls = view.get_serializer_class()
                
                # Assert
                if isinstance(expected_serializer_cls, str):
                    self.assertEqual(serializer_cls.__name__, expected_serializer_cls)
                else:
                    # default fallback
                    self.assertEqual(serializer_cls, expected_serializer_cls)

    def test_get_queryset_removes_filter_for_non_list(self):
        # Arrange
        view = DummySectorViewset(action="retrieve")
        
        # Uma forma mais limpa de simular a função filter_queryset
        original_filter_queryset = view.filter_queryset
        view.filter_queryset = lambda q=None: "qs"
        
        # Mock da queryset - temos que usar um objeto que seja iterável
        view.queryset = []
        
        # Act
        view.get_queryset()
        
        # Assert
        self.assertIsNone(view.filterset_class, 
                         "filterset_class deve ser None quando action != 'list'")
        
        # Restaurar o método original, embora não seja estritamente necessário
        view.filter_queryset = original_filter_queryset 