
import pandas as pd
import json
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib import messages
from django.db import IntegrityError
from operations.models import ContributionRecord
from accounts.models import CustomUser
from datetime import datetime

def bulk_upload_contributions(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_url = fs.path(filename)

        try:
            df = pd.read_excel(file_url)

            if not {'Email', 'Amount', 'Month', 'Year'}.issubset(df.columns):
                return JsonResponse({"error": "Invalid file format. Columns should be Email, Amount, Month, Year."}, status=400)

            preview_data = df.to_dict(orient='records')
            request.session['contributions_preview'] = preview_data  # Store for final submission
            return JsonResponse({"success": True, "preview_data": preview_data})  # Send JSON response
        
        except Exception as e:
            return JsonResponse({"error": f"Error processing file: {str(e)}"}, status=500)

    return render(request, 'operations/contributions/upload_contributions.html')

def confirm_bulk_upload(request):
    month_mapping = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    preview_data = request.session.get('contributions_preview', [])
    if not preview_data:
        return JsonResponse({"error": "No data to process."}, status=400)

    success_count, duplicate_count = 0, 0

    for row in preview_data:
        email, amount, month, year = row.get('Email'), row.get('Amount'), row.get('Month'), row.get('Year')
        user = CustomUser.objects.filter(email=email).first()
        
        month = month_mapping.get(month.lower(), None)  # Convert month to number

        if user:
            if ContributionRecord.objects.filter(employee=user, month=month, year=year).exists():
                duplicate_count += 1
                continue

            try:
                ContributionRecord.objects.create(
                    employee=user,
                    amount=amount,
                    month=month,
                    year=year,
                    status='paid'
                )
                success_count += 1
            except IntegrityError:
                duplicate_count += 1

    del request.session['contributions_preview']
    return JsonResponse({"success": True, "uploaded": success_count, "duplicates": duplicate_count})
