import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from django.test import TransactionTestCase
# support for custom User models in Django 1.5+
from djangoratings.exceptions import *
from testapp.models import RatingTestModel
from djangoratings.models import Vote, SimilarUser, IgnoredObject

User = get_user_model()

settings.RATINGS_VOTES_PER_IP = 1


class RatingTestCase(TransactionTestCase):
    def testRatings(self):
        instance = RatingTestModel.objects.create()

        # Test adding votes
        instance.rating.add(score=1, user=None, ip_address='127.0.0.1')
        self.assertEqual(instance.rating.score, 1)
        self.assertEqual(instance.rating.votes, 1)

        # Test adding votes
        instance.rating.add(score=2, user=None, ip_address='127.0.0.2')
        self.assertEqual(instance.rating.score, 3)
        self.assertEqual(instance.rating.votes, 2)

        # Test changing of votes
        instance.rating.add(score=2, user=None, ip_address='127.0.0.1')
        self.assertEqual(instance.rating.score, 4)
        self.assertEqual(instance.rating.votes, 2)

        # Test users
        user = User.objects.create(username=str(random.randint(0, 100000000)))
        user2 = User.objects.create(username=str(random.randint(0, 100000000)))

        instance.rating.add(score=2, user=user, ip_address='127.0.0.3')
        self.assertEqual(instance.rating.score, 6)
        self.assertEqual(instance.rating.votes, 3)

        instance.rating2.add(score=2, user=user, ip_address='127.0.0.3')
        self.assertEqual(instance.rating2.score, 2)
        self.assertEqual(instance.rating2.votes, 1)

        self.assertRaises(IPLimitReached, instance.rating2.add, score=2, user=user2, ip_address='127.0.0.3')

        # Test deletion hooks
        Vote.objects.filter(ip_address='127.0.0.3').delete()

        instance = RatingTestModel.objects.get(pk=instance.pk)

        self.assertEqual(instance.rating.score, 4)
        self.assertEqual(instance.rating.votes, 2)
        self.assertEqual(instance.rating2.score, 0)
        self.assertEqual(instance.rating2.votes, 0)

class RecommendationsTestCase(TransactionTestCase):
    def setUp(self):
        self.instance = RatingTestModel.objects.create()
        self.instance2 = RatingTestModel.objects.create()
        self.instance3 = RatingTestModel.objects.create()
        self.instance4 = RatingTestModel.objects.create()
        self.instance5 = RatingTestModel.objects.create()

        # Test users
        self.user = User.objects.create(username=str(random.randint(0, 100000000)))
        self.user2 = User.objects.create(username=str(random.randint(0, 100000000)))

    def testExclusions(self):
        Vote.objects.all().delete()

        self.instance.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance2.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance3.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance4.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance5.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')

        # we should only need to call this once
        SimilarUser.objects.update_recommendations()

        self.assertEqual(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2,
                                                            RatingTestModel))
        self.assertEqual(len(recs), 4)

        ct = ContentType.objects.get_for_model(RatingTestModel)

        IgnoredObject.objects.create(user=self.user2, content_type=ct, object_id=self.instance2.pk)

        recs = list(SimilarUser.objects.get_recommendations(self.user2,
                                                            RatingTestModel))
        self.assertEqual(len(recs), 3)

        IgnoredObject.objects.create(user=self.user2, content_type=ct, object_id=self.instance3.pk)
        IgnoredObject.objects.create(user=self.user2, content_type=ct, object_id=self.instance4.pk)

        recs = list(SimilarUser.objects.get_recommendations(self.user2,
                                                            RatingTestModel))
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs, [self.instance5])

        self.instance5.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')
        recs = list(SimilarUser.objects.get_recommendations(self.user2,
                                                            RatingTestModel))
        self.assertEqual(len(recs), 0)

    def testSimilarUsers(self):
        Vote.objects.all().delete()

        self.instance.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance2.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance3.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance4.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance5.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')
        self.instance2.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')
        self.instance3.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')

        SimilarUser.objects.update_recommendations()

        self.assertEqual(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2,
                                                            RatingTestModel))
        self.assertEqual(len(recs), 2)

        self.instance4.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')

        SimilarUser.objects.update_recommendations()

        self.assertEqual(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2,
                                                            RatingTestModel))
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs, [self.instance5])

        self.instance5.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')

        SimilarUser.objects.update_recommendations()

        self.assertEqual(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2,
                                                            RatingTestModel))
        self.assertEqual(len(recs), 0)
