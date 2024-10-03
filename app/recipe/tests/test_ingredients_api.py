from decimal import Decimal

from django.contrib.auth import get_user_model

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient
from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')

def create_user(email='user@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email, password)
    
def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])

    
    
class PublicIngredientsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        
    def test_auth_required(self):
        res = self.client.get(INGREDIENTS_URL)
        
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        

class PrivateIngredientApiTests(TestCase):
    
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        
    def test_retrive_ingredients(self):
        
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Vanila')
        
        res = self.client.get(INGREDIENTS_URL)
        
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        self.assertEqual(res.data, serializer.data)
        
    def test_ingredients_limited_to_user(self):
        
        user2 = create_user(email='u2@example.com')
        Ingredient.objects.create(user=user2, name='Salt')
        ingredient = Ingredient.objects.create(user=self.user, name='papre')
        
        res = self.client.get(INGREDIENTS_URL)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)
        
        
    def test_update_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user, name='cilantro')
        
        payload = {'name' : 'Coriander'}
        
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])
        
        
    def test_delete_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user, name='Lettuce')
        
        url = detail_url(ingredient.id)
        res = self.client.delete(url)
        
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())
        
    def test_filter_ingredients_assigend_to_recipe(self):
        ''' test listing ingredinents by those assiged to recipe'''
        
        ing1 = Ingredient.objects.create(user=self.user, name='ing 1')
        ing2 = Ingredient.objects.create(user=self.user, name='ing 2')
        recipe = Recipe.objects.create(
            title='title1',
            time_minutes = 5,
            price=Decimal('43'),
            user=self.user
        )
        recipe.ingredients.add(ing1)
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)
        
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)
        
    def test_filtered_ingredients_unique(self):
        ing = Ingredient.objects.create(user=self.user, name='ing1')
        recipe1 = Recipe.objects.create(
            title = 'title1',
            time_minutes = 43, 
            price=Decimal('3.4'),
            user=self.user
        )
        
        recipe2 = Recipe.objects.create(
            title = 'title2',
            time_minutes = 43, 
            price=Decimal('3.4'),
            user=self.user
        )
        
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)
        
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)