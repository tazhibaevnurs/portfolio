from django import forms

from main.models import ClientBenefit, Project
from main.services.enrichment import LLM_CARD_FIELD_KEYS


class ProjectDashboardForm(forms.ModelForm):
    tech_tags_text = forms.CharField(
        required=False,
        label='Стек (через запятую)',
        widget=forms.TextInput(attrs={'placeholder': 'Django, PostgreSQL, Redis'}),
    )
    deployment_platforms_text = forms.CharField(
        required=False,
        label='Платформы (через запятую)',
        help_text='Например: Vercel, Neon, GitHub Actions — для блока «платформы» на карточке.',
        widget=forms.TextInput(attrs={'placeholder': 'Vercel, PostgreSQL, AWS'}),
    )

    class Meta:
        model = Project
        fields = [
            'title',
            'author_notes',
            'git_repository_url',
            'is_visible',
            'sort_order',
            'display_title',
            'category',
            'summary',
            'stat1_value',
            'stat1_label',
            'stat2_value',
            'stat2_label',
            'demo_url',
            'pagespeed_public_report_url',
            'pagespeed_cwv_note',
            'pagespeed_diag_good',
            'pagespeed_diag_bad',
            'pagespeed_profile_note',
            'card_image',
            'card_image_url',
            'icon_emoji',
        ]
        widgets = {
            'author_notes': forms.Textarea(attrs={'rows': 5}),
            'summary': forms.Textarea(attrs={'rows': 4}),
            'git_repository_url': forms.URLInput(
                attrs={'placeholder': 'https://github.com/user/repo'}
            ),
            'pagespeed_public_report_url': forms.URLInput(
                attrs={
                    'placeholder': 'https://pagespeed.web.dev/analysis?url=...',
                }
            ),
            'pagespeed_cwv_note': forms.TextInput(
                attrs={'placeholder': 'Напр.: Оценка CWV: только лаборатория — полевых данных CrUX нет.'}
            ),
            'pagespeed_diag_good': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'По одной фразе на строку: что уже хорошо.'}
            ),
            'pagespeed_diag_bad': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'По одной фразе на строку: узкие места.'}
            ),
            'pagespeed_profile_note': forms.TextInput(
                attrs={
                    'placeholder': 'Напр.: лёгкий лендинг — другой профиль, чем тяжёлый SPA.',
                }
            ),
            'sort_order': forms.NumberInput(attrs={'min': 0, 'step': 1}),
            'card_image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'card_image_url': forms.URLInput(
                attrs={'placeholder': 'https://example.com/hero-screenshot.webp'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tech_tags_text'].initial = ', '.join(self.instance.tech_tags or [])
            self.fields['deployment_platforms_text'].initial = ', '.join(
                self.instance.deployment_platforms or []
            )
        frozen = list(self.instance.llm_frozen_fields or []) if self.instance.pk else []
        for key in LLM_CARD_FIELD_KEYS:
            name = f'freeze_{key}'
            self.fields[name] = forms.BooleanField(
                required=False,
                label='',
                initial=(key in frozen),
                widget=forms.CheckboxInput(
                    attrs={
                        'class': 'freeze-llm',
                        'title': 'Не перезаписывать при обогащении LLM',
                    }
                ),
            )

    def clean(self):
        cleaned = super().clean()
        raw = ''
        if cleaned is not None:
            raw = cleaned.get('tech_tags_text') or ''
        if not raw:
            raw = self.data.get('tech_tags_text', '') or ''
        self._parsed_tags = [
            p.strip() for p in raw.replace(';', ',').split(',') if p.strip()
        ]
        plat = ''
        if cleaned is not None:
            plat = cleaned.get('deployment_platforms_text') or ''
        if not plat:
            plat = self.data.get('deployment_platforms_text', '') or ''
        self._parsed_platforms = [
            p.strip() for p in plat.replace(';', ',').split(',') if p.strip()
        ]
        self._frozen_keys = []
        if cleaned is not None:
            for key in LLM_CARD_FIELD_KEYS:
                if cleaned.get(f'freeze_{key}'):
                    self._frozen_keys.append(key)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.tech_tags = getattr(self, '_parsed_tags', obj.tech_tags or [])
        obj.deployment_platforms = getattr(self, '_parsed_platforms', obj.deployment_platforms or [])
        obj.llm_frozen_fields = list(getattr(self, '_frozen_keys', []) or [])
        if commit:
            obj.save()
        return obj


class ClientBenefitForm(forms.ModelForm):
    class Meta:
        model = ClientBenefit
        fields = ['title', 'body', 'icon', 'sort_order', 'is_active']
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'rows': 8,
                    'placeholder': 'Коротко и по делу: выгода для заказчика.',
                }
            ),
            'icon': forms.TextInput(
                attrs={
                    'placeholder': 'Например 📋 или оставьте пустым',
                    'maxlength': 16,
                }
            ),
            'sort_order': forms.NumberInput(attrs={'min': 0, 'step': 1}),
        }
