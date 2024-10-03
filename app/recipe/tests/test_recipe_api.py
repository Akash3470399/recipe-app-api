from decimal import Decimal

from django.contrib.auth import get_user_model

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **parms):
    defaults = {
        'title' : 'Sample Recipe',
        'time_minutes' : 22, 
        'price' : Decimal('5.25'),
        'description' : 'Sample description',
        'link' : 'http://example.com/recipe.pdf',
        
    }
    
    defaults.update(parms)
    
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe



def create_user(**params):
    return get_user_model().objects.create_user(**params)

class PublicRecipeAPITests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        
    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)
        
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
class PrivateRecipeApiTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        # self.user = get_user_model().objects.create_user(
        #     'user@example.com',
        #     'testpass123'
        # )
        self.user = create_user(email='user@exmple.com', password='testpass123')
        self.client.force_authenticate(self.user)
        
    def test_retrive_recipes(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)
        
        res = self.client.get(RECIPE_URL)
        
        recipe = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipe, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_recipe_list_limited_to_user(self):
        other_user = create_user(    
            email = 'other@example.com',
            password = 'password123'
        )
        
        create_recipe(user=other_user)
        create_recipe(user=self.user)
        
        res = self.client.get(RECIPE_URL)
        
        recipes = Recipe.objects.filter(user=self.user)
        
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        
        
    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)
        
        url = detail_url(recipe_id=recipe.id)
        res = self.client.get(url)
        
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)
        
    def test_create_recipe(self):
        payload = {
            'title' : 'sample recipe',
            'time_minutes' : 43,
            'price' : Decimal("5.99")
        }

        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)
    
    def test_partial_update(self):
        
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(user=self.user,
                               title = 'smaple title',
                               link = original_link
                               )
        payload = {'title' : "new Updated Title"}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)
        
    def test_full_update(self):
        
        recipe = create_recipe(user=self.user,
                               title = 'smaple title',
                               link = 'https://example.com/recipe.pdf',
                               description = 'new description'
                               )
        
        payload = {
            'title' : 'New recipe title',
            'link' : 'https://example.com/new-recipe.pdf',
            'description' : 'New desc',
            'time_minutes' : 50,
            'price' : Decimal('2.50')
        }
        
        url = detail_url(recipe_id=recipe.id)
        res = self.client.put(url, payload)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)
        
    def test_update_user_returns_error(self):
        
        new_user = create_user(email='test@exampl.com', password = 'newpass')
        recipe = create_recipe(user=self.user)
        
        payload = {'user' : new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)
        
    def test_detete_recipe(self):
        recipe = create_recipe(user=self.user)
        
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())
        
    def test_delete_other_users_recipe_error(self):
        new_user = create_user(
            email='user2@example.com',
            password='newpass123'
        )
        recipe = create_recipe(user=new_user)
        
        url = detail_url(recipe.id)
        
        res = self.client.delete(url)
        
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
        
    def test_create_recipe_with_new_tags(self):
        payload = {
            'title': 'Thaii prawn curry',
            'time_minutes' : 38,
            'price' : Decimal('2.43'),
            'tags' : [{'name' : 'Thai'}, {'name' : 'Dinner'}]
        }
        
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)
    
    
    def test_create_recipe_with_existing_tags(self):
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title' : 'Pongal',
            'time_minutes' : 60, 
            'price' : Decimal('5.3'),
            'tags' : [{'name' : 'Indian'}, {'name':'Breakfast'}]
        }
        
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)
    
    def test_create_tag_on_update(self):
        recipe = create_recipe(user=self.user)
        payload = {'tags' : [{'name':'Lunch'}]}
        
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())
        
    def test_update_recipe_assigned_tag(self):
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)
        
        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags' : [{'name' : 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())
        
    def test_clear_recipe_tags(self):
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)
        
        payload = {'tags': []}
        
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
        
        
    def test_create_recipe_with_new_ingredients(self):
        
        payload = {
            'title' : 'new recipe',
            'time_minutes' : 54,
            'price' : Decimal('4.6'),
            'ingredients' : [{'name' : 'ing1'}, {'name' : 'ing2'}]
        }
        
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)
            
    def test_create_recipe_with_existing_ingredient(self):
        
        ingredient = Ingredient.objects.create(user=self.user, name='lemon')
        payload = {
            'title' : 'new recipe',
            'time_minutes' : 54,
            'price' : Decimal('4.6'),
            'ingredients' : [{'name' : 'lemon'}, {'name' : 'ing2'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)
            
    def test_create_ingredient_on_update(self):
        
        recipe = create_recipe(user=self.user)
        payload = {'ingredients': [{'name':'ing1'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        new_ingredient = Ingredient.objects.get(user=self.user, name='ing1')
        self.assertIn(new_ingredient, recipe.ingredients.all())
     
    def test_update_recipe_assign_ingredient(self):
        ingredient1 = Ingredient.objects.create(user=self.user, name='ing1')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)   
        
        ingredient2 = Ingredient.objects.create(user=self.user, name='Chilli')
        payload = {'ingredients' : [{'name' : 'Chilli'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())
        
    def test_clear_recipe_ingredients(self):
        ingredient = Ingredient.objects.create(
            user=self.user, name='garlic')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)
        
        payload = {'ingredients' : []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)