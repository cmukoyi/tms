-- =====================================================
-- Script 01: Create Database
-- Tender Management System (TMS)
-- =====================================================
-- Description: Creates the main database for TMS
-- Run this first as a MySQL admin user
-- =====================================================

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS tms_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- Use the database
USE tms_db;

-- Display confirmation
SELECT 'Database tms_db created successfully' AS Status;
