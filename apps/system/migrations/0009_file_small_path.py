from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0008_user_gender'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='small_path',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='缩略图地址'),
        ),
    ]
